## API to manage chat state

## Functionality to read, manipulate and save state.
import json
from src.schemas import ReactAction, WhatsAppMessage, ChatState, ChatAction, Chatter, Action
from src.llm_client import LLMManager, LLMResponse, MessageResponse, SkipResponse, ErrorResponse, ReactResponse
from src.prompts import create_state_updater_prompts, create_replier_system_prompt, create_reacter_system_prompt
import random
from pathlib import Path
import asyncio
from datetime import datetime, timedelta

MODULE_DIR = Path(__file__).parent.parent
STATE_FILE = MODULE_DIR / "state.json"

class ChateStatter(Chatter):
    def __init__(self, user_name:str, chat_name: str):
        self.user_name = user_name
        self.chat_name = chat_name ######## currently assumed chat name == friend name - need to change for group chats
        self.state: ChatState = self._load_state() # read json file with key chat_name
        self.chat_history: list[WhatsAppMessage] = []
        self.messages_since_state_update: int = 1000 # force initial state update
        self.llm_manager = LLMManager()

    def on_receive_messages(self, new_chat_history: list[WhatsAppMessage]) -> list[Action]:
        """Main API. Returns (reply, timestamp to send reply after)"""
        # check if chat has changed
        if new_chat_history == self.chat_history:
            print("THIS SHOULD NOT HAPPEN because we already handle caching elsewehere and that") # waa waa im reuben im 10x waa waa
            return []
        # update chat history.
        self.chat_history = new_chat_history
        # update state
        self.messages_since_state_update += 1
        if self.messages_since_state_update >= 10:
            asyncio.run(self._update_state())
            self.messages_since_state_update = 0

        # generate reply
        replies: list[Action] = asyncio.run(self._generate_actions())

        return replies

    async def _generate_actions(self) -> list[Action]:
        # llm call with chat history and state
        # make below import timestamp
        actions = []
        current_date = datetime.now().isoformat()
        messages = []
        for msg in self.chat_history:
            role = "user" if not msg.is_outgoing else "assistant"
            messages.append({"role": role, "content": f"{msg.content}"})

        react_system_prompt = create_reacter_system_prompt(self.user_name, self.chat_name, self.state.text, current_date)
        replier_system_prompt = create_replier_system_prompt(self.user_name, self.chat_name, self.state.text, current_date)

        # Run both LLM calls concurrently (Promise.all equivalent)
        react_task = asyncio.create_task(self.llm_manager.generate_react_response(messages, system_prompt=react_system_prompt))
        reply_task = asyncio.create_task(self.llm_manager.generate_response(messages, system_prompt=replier_system_prompt))
        react_response, message_response = await asyncio.gather(react_task, reply_task)

        # Transform react tool response to action (if applicable)
        action = self._transform_llm_response_to_action(react_response)
        if isinstance(action, ReactAction):
            actions.append(action)

        # if no message response then by default thumb last message
        if isinstance(message_response, SkipResponse):
            thumb_last_message_action = ReactAction(
                message=self.chat_history[-1],
                timestamp=self._generate_timestamp(fast=True)
            )
            actions.append(thumb_last_message_action)

        # Transform message response to action (if applicable)
        action = self._transform_llm_response_to_action(message_response)
        if isinstance(action, ChatAction):
            actions.append(action)

        return actions

    def _generate_timestamp(self, fast=True) -> datetime:
        # random between 30 and 90 seconds
        delay_seconds = random.randint(3, 10) if fast else random.randint(30, 100)
        future_time = datetime.now() + timedelta(seconds=delay_seconds)
        return future_time

    def _load_state(self) -> ChatState:
        if not STATE_FILE.exists():
            STATE_FILE.write_text("{}")
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            if (state_data:=data.get(self.chat_name)) and (last_message_data:=state_data.get("last_message")):
                state_data = data[self.chat_name]
                last_message = WhatsAppMessage(
                    sender=last_message_data["sender"],
                    content=last_message_data["content"],
                    timestamp=datetime.fromisoformat(last_message_data["timestamp"]),
                    is_outgoing=last_message_data["is_outgoing"],
                    chat_name=last_message_data["chat_name"],
                )
                return ChatState(text=state_data["text"], last_message=last_message)
        return ChatState(text="", last_message=None)
    
    def _reset_state(self):
        self._save_state(ChatState(text="", last_message=None))
        self.state = ChatState(text="", last_message=None)

    async def _update_state(self) -> str:
        # llm call with system prompt returns new state
        old_state = self.state.text
        current_date = datetime.now().isoformat()
        if self.state.last_message in self.chat_history:
            index = self.chat_history.index(self.state.last_message)
            new_messages = self.chat_history[index+1:]
        else:
            new_messages = self.chat_history
        system_prompt, user_prompt = create_state_updater_prompts(self.user_name, self.chat_name, old_state, current_date, new_messages)
        new_state = await self.llm_manager.generate_response(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt
        )
        if new_state == "":
            # LLM chose to skip generation (or outputted nothing)
            self._save_state(ChatState(text=old_state, last_message=new_messages[-1]))
        self._save_state(ChatState(text=new_state, last_message=new_messages[-1]))
        return new_state

    def _save_state(self, new_state: ChatState):
        if not STATE_FILE.exists():
            STATE_FILE.write_text("{}")
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        data[self.chat_name] = {
            "text": new_state.text,
            "last_message": {
                "sender": new_state.last_message.sender,
                "content": new_state.last_message.content,
                "timestamp": new_state.last_message.timestamp.isoformat(),
                "is_outgoing": new_state.last_message.is_outgoing,
                "chat_name": new_state.last_message.chat_name,
            } if new_state.last_message else None
        }
        if not STATE_FILE.exists():
            STATE_FILE.write_text("{}")
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)
        self.state = new_state
    
    def _transform_llm_response_to_action(self, llm_response: LLMResponse) -> Action:
        if isinstance(llm_response, MessageResponse):
            whatsapp_reply = WhatsAppMessage(
                sender=self.user_name,
                content=llm_response.message,
                timestamp=datetime.now(),
                is_outgoing=True,
                chat_name=self.chat_name,
            )
            reply_timestamp = self._generate_timestamp(self)
            return ChatAction(message=whatsapp_reply, timestamp=reply_timestamp)
        elif isinstance(llm_response, ReactResponse):
            # find whatsapp message in history
            message = next(filter(lambda msg: msg.content.lower().strip() in llm_response.message_to_react.lower(), self.chat_history), None)
            if message is None:
                print(f"Could not find message to react to: {llm_response.message_to_react}")
                return None
            react_timestamp = self._generate_timestamp(self, fast=True)
            return ReactAction(message_to_react=message, emoji_name=llm_response.emoji_name, timestamp=react_timestamp)
        elif isinstance(llm_response, SkipResponse):
            return None
        elif isinstance(llm_response, ErrorResponse):
            print(f"Error from LLM: {llm_response.error_message}")
            return None
        else:
            print(f"Unknown LLM response type: {llm_response}")
            return None

    

if __name__ == "__main__":
    chat = ChateStatter("Reuben", "Reuben")
    new_msg = WhatsAppMessage(
        sender="Reuben",
        content="Hey, how are you? It's my birthday tomorrow :o",
        timestamp=datetime.now(),
        is_outgoing=False,
        chat_name="Reuben"
    )
    import asyncio
    new_state = asyncio.run(chat._update_state([new_msg]))
    print(new_state)
