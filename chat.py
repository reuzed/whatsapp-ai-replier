## API to manage chat state

## Functionality to read, manipulate and save state.

from datetime import datetime
import json
from schemas import WhatsAppMessage, ChatState
from llm_client import LLMManager
from prompts import create_state_updater_prompts
import random
CHAT_HISTORY_LIMIT = 20
STATE_FILE = "state.json"

class Chat:
    def __init__(self, chat_name: str):
        self.chat_name = chat_name
        self.state: ChatState = self.load_state() # read json file with key chat_name

        # get_messages_since_state_update() -> use all since state update (or all) to update state put last 20 in chat_history.
        # update state if new messages
        self.chat_history: list[WhatsAppMessage] = []
        self.messages_since_state_update: int = 0
        self.llm_manager = LLMManager()
        pass

    async def reply_to_message(self, message: WhatsAppMessage) -> str:
        self.chat_history.append(message)
        if len(self.chat_history) > CHAT_HISTORY_LIMIT:
            self.chat_history = self.chat_history[-CHAT_HISTORY_LIMIT:]
        self.messages_since_state_update += 1
        if self.messages_since_state_update >= 10:
            await self.update_state(self.chat_history)
            self.messages_since_state_update = 0
        # llm call with chat history and state
        # make below import timestamp
        messages = [{"role": "system", "content": f"You are a helpful assistant. The current chat state is: {self.state.text}"}]
        for msg in self.chat_history:
            role = "user" if not msg.is_outgoing else "assistant"
            messages.append({"role": role, "content": f"{msg.sender}: {msg.content}"})
        response = await self.llm_manager.generate_response(messages)
        return response

    def generate_reply_time_seconds(self, fast=True) -> int:
        # random between 30 and 90 seconds
        return random.randint(10, 30) if fast else random.randint(30, 100)

    def load_state(self) -> ChatState:
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

    async def update_state(self, messages: list[WhatsAppMessage]) -> str:
        # llm call with system prompt returns new state
        current_date = datetime.now().isoformat()
        system_prompt, user_prompt = create_state_updater_prompts(self.state.text, current_date, messages)
        new_state = await self.llm_manager.generate_response(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt
        )
        self.save_state(ChatState(text=new_state, last_message=messages[-1]))
        return new_state

    def save_state(self, new_state: ChatState):
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
