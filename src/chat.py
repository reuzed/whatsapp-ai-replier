## API to manage chat state

## Functionality to read, manipulate and save state.

from datetime import datetime
import json
from schemas import WhatsAppMessage, ChatState
from llm_client import LLMManager
from prompts import create_state_updater_prompts, create_replier_system_prompt
import random
STATE_FILE = "state.json"

class Chat:
    def __init__(self, receiver_name: str):
        self.receiver_name = receiver_name
        self.state: ChatState = self.load_state() # read json file with key receiver_name
        self.chat_history: list[WhatsAppMessage] = []
        self.messages_since_state_update: int = 1000 # force initial state update
        self.llm_manager = LLMManager()

    async def on_messages_received(self, new_chat_history: list[WhatsAppMessage]) -> tuple[WhatsAppMessage, str]:
        """Main API. Returns (reply, timestamp to send reply after)"""
        # update chat history.
        self.chat_history = new_chat_history
        # update state
        self.messages_since_state_update += 1
        if self.messages_since_state_update >= 10:
            await self.update_state()
            self.messages_since_state_update = 0
        # generate reply
        reply = await self._reply()
        # generate reply time
        reply_timestamp = self._generate_reply_timestamp(self)

        return reply, reply_timestamp

    
    async def _reply(self) -> str:
        # llm call with chat history and state
        # make below import timestamp
        current_date = datetime.now().isoformat()
        system_prompt = create_replier_system_prompt(self.state.text, current_date)
        messages = []
        for msg in self.chat_history:
            role = "user" if not msg.is_outgoing else "assistant"
            messages.append({"role": role, "content": f"{msg.sender}: {msg.content}"})
        response = await self.llm_manager.generate_response(messages, system_prompt=system_prompt)
        return response

    def _generate_reply_timestamp(self, fast=True) -> str:
        # random between 30 and 90 seconds
        delay_seconds = random.randint(10, 30) if fast else random.randint(30, 100)
        future_time = datetime.now() + datetime.timedelta(seconds=delay_seconds)
        return future_time.isoformat()

    def _load_state(self) -> ChatState:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            if self.chat_name in data:
                state_data = data[self.chat_name]
                last_message_data = state_data["last_message"]
                last_message = WhatsAppMessage(
                    sender=last_message_data["sender"],
                    content=last_message_data["content"],
                    timestamp=datetime.fromisoformat(last_message_data["timestamp"]),
                    is_outgoing=last_message_data["is_outgoing"],
                    chat_name=last_message_data["chat_name"],
                )
                return ChatState(text=state_data["text"], last_message=last_message)
        return ChatState(text="", last_message=None)

    async def _update_state(self) -> str:
        # llm call with system prompt returns new state
        current_date = datetime.now().isoformat()
        if self.state.last_message in self.chat_history:
            index = self.chat_history.index(self.state.last_message)
            new_messages = self.chat_history[index+1:]
        else:
            new_messages = self.chat_history
        system_prompt, user_prompt = create_state_updater_prompts(self.state.text, current_date, new_messages)
        new_state = await self.llm_manager.generate_response(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt
        )
        self.save_state(ChatState(text=new_state, last_message=new_messages[-1]))
        return new_state

    def _save_state(self, new_state: ChatState):
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
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)
        self.state = new_state

if __name__ == "__main__":
    chat = Chat("Reuben")
    new_msg = WhatsAppMessage(
        sender="Reuben",
        content="Hey, how are you? It's my birthday tomorrow :o",
        timestamp=datetime.now(),
        is_outgoing=False,
        chat_name="Reuben"
    )
    import asyncio
    new_state = asyncio.run(chat.update_state([new_msg]))
    print(new_state)
