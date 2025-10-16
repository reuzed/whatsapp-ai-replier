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
from src.state_maintenance import StateMaintenance

class ChateStatter(Chatter):
    def __init__(self, user_name:str):
        self.user_name = user_name
        self.state_maintenance = StateMaintenance(self.user_name) # read json file with key chat_name
        self.messages_since_state_update: int = 1000 # force initial state update
        self.llm_manager = LLMManager()

    def on_receive_messages(self, new_chat_history: list[WhatsAppMessage], chat_name: str) -> list[Action]:
        """Main API. Returns (reply, timestamp to send reply after)"""
        # update state
        self.messages_since_state_update += 1
        if self.messages_since_state_update >= 10:
            asyncio.run(self.state_maintenance.update_state(chat_name, new_chat_history))
            self.messages_since_state_update = 0

        # generate reply
        replies: list[Action] = asyncio.run(self._generate_actions(new_chat_history, chat_name))

        return replies

    async def _generate_actions(self, new_chat_history: list[WhatsAppMessage], chat_name: str) -> list[Action]:
        # llm call with chat history and state
        # make below import timestamp
        actions = []
        current_date = datetime.now().isoformat()
        messages = []
        for msg in new_chat_history:
            role = "user" if not msg.is_outgoing else "assistant"
            messages.append({"role": role, "content": f"{msg.content}"})

        state_text = self.state_maintenance.load_friend_state(chat_name).text
        react_system_prompt = create_reacter_system_prompt(self.user_name, chat_name, state_text, current_date)
        replier_system_prompt = create_replier_system_prompt(self.user_name, chat_name, state_text, current_date)

        # Run both LLM calls concurrently (Promise.all equivalent)
        react_task = asyncio.create_task(self.llm_manager.generate_react_response(messages, system_prompt=react_system_prompt))
        reply_task = asyncio.create_task(self.llm_manager.generate_response(messages, system_prompt=replier_system_prompt))
        react_response, message_response = await asyncio.gather(react_task, reply_task)

        # Transform react tool response to action (if applicable)
        action = self._transform_llm_response_to_action(react_response, new_chat_history, chat_name)
        if isinstance(action, ReactAction):
            actions.append(action)

        # if no message response then by default thumb last message
        if isinstance(message_response, SkipResponse):
            thumb_last_message_action = ReactAction(
                message_to_react=new_chat_history[-1],
                emoji_name="clown", # want thumbs up, but this doesn't work due to multiple same name emojis
                timestamp=self._generate_timestamp(fast=True)
            )
            actions.append(thumb_last_message_action)

        # Transform message response to action (if applicable)
        action = self._transform_llm_response_to_action(message_response, new_chat_history, chat_name)
        if isinstance(action, ChatAction):
            actions.append(action)

        return actions

    def _generate_timestamp(self, fast=True) -> datetime:
        # random between 30 and 90 seconds
        delay_seconds = random.randint(3, 10) if fast else random.randint(30, 100)
        future_time = datetime.now() + timedelta(seconds=delay_seconds)
        return future_time
    
    def _transform_llm_response_to_action(self, llm_response: LLMResponse, new_chat_history: list[WhatsAppMessage], chat_name: str) -> Action:
        if isinstance(llm_response, MessageResponse):
            whatsapp_reply = WhatsAppMessage(
                sender=self.user_name,
                content=llm_response.text,
                timestamp=datetime.now(),
                is_outgoing=True,
                chat_name=chat_name,
            )
            reply_timestamp = self._generate_timestamp()
            return ChatAction(message=whatsapp_reply, timestamp=reply_timestamp)
        elif isinstance(llm_response, ReactResponse):
            # find whatsapp message in history
            message = next(filter(lambda msg: msg.content.lower().strip() in llm_response.message_to_react.lower(), new_chat_history), None)
            if message is None:
                print(f"Could not find message to react to: {llm_response.message_to_react}")
                return None
            react_timestamp = self._generate_timestamp(fast=True)
            return ReactAction(message_to_react=message, emoji_name=llm_response.emoji_name, timestamp=react_timestamp)
        elif isinstance(llm_response, SkipResponse):
            return None
        elif isinstance(llm_response, ErrorResponse):
            print(f"Error from LLM: {llm_response.error_message}")
            return None
        # should be one of these options


if __name__ == "__main__":
    chat = ChateStatter("Bob")
    new_msg = WhatsAppMessage(
        sender="Bob",
        content="Hey, how are you? It's my mum's birthday in 2 days :o",
        timestamp=datetime.now(),
        is_outgoing=False,
        chat_name="Bob"
    )
    import asyncio
    print("sjdflsjkfs")
    asyncio.run(chat.state_maintenance.update_state("Bob", [new_msg]))
