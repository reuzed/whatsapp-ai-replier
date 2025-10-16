## Class for managing the state files

import json
from src.schemas import WhatsAppMessage, ChatState
from src.llm_client import LLMManager, MessageResponse, SkipResponse
from src.prompts import create_state_updater_prompts
from pathlib import Path
from datetime import datetime

MODULE_DIR = Path(__file__).parent.parent
STATE_FILE = MODULE_DIR / "state.json"

class StateMaintenance:
    def __init__(self, user_name: str):
        self.state_file = STATE_FILE
        self.user_name = user_name
        self.llm_manager = LLMManager()

    def load_friend_state(self, chat_name: str) -> ChatState:
        if not STATE_FILE.exists():
            STATE_FILE.write_text("{}")
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            if (state_data:=data.get(chat_name)) and (last_message_data:=state_data.get("last_message")):
                state_data = data[chat_name]
                last_message = WhatsAppMessage(
                    sender=last_message_data["sender"],
                    content=last_message_data["content"],
                    timestamp=datetime.fromisoformat(last_message_data["timestamp"]),
                    is_outgoing=last_message_data["is_outgoing"],
                    chat_name=last_message_data["chat_name"],
                )
                seen_messages = data
                return ChatState(text=state_data["text"], last_message=last_message)
        return ChatState(text="", last_message=None)

    async def update_state(self, chat_name: str, chat_history: list[WhatsAppMessage]):
        # llm call with system prompt
        old_state = self.load_friend_state(chat_name)
        last_message = old_state.last_message
        old_state_text = old_state.text
        current_date = datetime.now().isoformat()
        if last_message in chat_history:
            index = chat_history.index(last_message)
            new_messages = chat_history[index+1:]
        else:
            new_messages = chat_history
        state_system_prompt, state_user_prompt = create_state_updater_prompts(self.user_name, chat_name, old_state_text, current_date, new_messages)
        response = await self.llm_manager.generate_response(
            messages=[{"role": "user", "content": state_user_prompt}],
            system_prompt=state_system_prompt,
            allow_skip=False
        )
        if isinstance(response, SkipResponse):
            # LLM chose to skip generation (or outputted nothing)
            self.save_state(ChatState(text=old_state_text, last_message=new_messages[-1]), chat_name)
        elif isinstance(response, MessageResponse):
            new_state_text = response.text
            self.save_state(ChatState(text=new_state_text, last_message=new_messages[-1]), chat_name)
        # should not have other options

    def reset_state(self, chat_name: str):
        self.save_state(ChatState(text="", last_message=None), chat_name)

    def save_state(self, new_state: ChatState, chat_name: str):
        if not STATE_FILE.exists():
            STATE_FILE.write_text("{}")
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        data[chat_name] = {
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
            print(STATE_FILE)
            json.dump(data, f, indent=4)