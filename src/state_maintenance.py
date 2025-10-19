## Class for managing the state files

import json
from src.schemas import WhatsAppMessage, ChatState
from src.llm_client import LLMManager, MessageResponse, SkipResponse
from src.prompts import create_state_updater_prompts
from pathlib import Path
from datetime import datetime

from rich import print

from typing import Literal, Any

MODULE_DIR = Path(__file__).parent.parent 
STATE_FILE = MODULE_DIR / "user_data/state.json"
MESSAGE_LOG_FILE = MODULE_DIR / "user_data/message_log.json"
     
MessageLog = dict[str, Any] #dict[Literal["content", "timestamp", "is_outgoing"], Any]

class StateMaintenance:
    def __init__(self, user_name: str):
        self.llm_manager = LLMManager()
        self.user_name = user_name

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
        """Assimilate new messages into existing state information with LLM call
        Writes to STATE_FILE (user_data/state.json)"""
        # llm call with system prompt
        old_state = self.load_friend_state(chat_name)
        last_message = old_state.last_message
        old_state_text = old_state.text
        old_state_len = len(old_state_text.split())
        current_date = datetime.now().isoformat()
        if last_message in chat_history:
            index = chat_history.index(last_message)
            new_messages = chat_history[index+1:]
        else:
            new_messages = chat_history
        state_system_prompt, state_user_prompt = create_state_updater_prompts(self.user_name, chat_name, old_state_text, old_state_len,current_date, new_messages)
        response = await self.llm_manager.generate_response(
            messages=[{"role": "user", "content": state_user_prompt}],
            system_prompt=state_system_prompt,
            allow_skip=False
        )
        if isinstance(response, SkipResponse):
            # LLM chose to skip generation (or outputted nothing)
            self.save_state(ChatState(text=old_state_text, last_message=chat_history[-1]), chat_name)
        elif isinstance(response, MessageResponse):
            new_state_text = response.text
            self.save_state(ChatState(text=new_state_text, last_message=chat_history[-1]), chat_name)
        # should not have other options

    def reset_state(self, chat_name: str):
        """Overwrite state with a blank version."""
        self.save_state(ChatState(text="", last_message=None), chat_name)

    def save_state(self, new_state: ChatState, chat_name: str):
        """Save chat state to the STATE_FILE file, if not existing, create this file at the correct location"""
        if not STATE_FILE.exists():
            STATE_FILE.write_text("{}")
        with open(STATE_FILE, "r") as f:
            state_data = json.load(f)
        state_data[chat_name] = {
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
            print("[red]Saving state file:s[/red]")
            print(STATE_FILE)
            json.dump(state_data, f, indent=4)

    def log_seen_messages(self, messages: list[WhatsAppMessage]):
        if not MESSAGE_LOG_FILE.exists():
            MESSAGE_LOG_FILE.write_text("{}")
        with open(MESSAGE_LOG_FILE, "r") as f:
            message_data:MessageLog = json.load(f)
        for message in messages:
            if message.chat_name not in message_data:
                message_data[message.chat_name] = []
            message_data[message.chat_name].append({
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "is_outgoing": message.is_outgoing,
            })
            message_data[message.chat_name] = dedupe_messages(message_data[message.chat_name])
        with open(MESSAGE_LOG_FILE, "w") as f:
            json.dump(message_data, f, indent=4)
    
    def get_seen_messages(self, chat_name: str, limit: int = 20) -> list[WhatsAppMessage]:
        if not MESSAGE_LOG_FILE.exists():
            MESSAGE_LOG_FILE.write_text("{}")
            return []
        with open(MESSAGE_LOG_FILE, "r") as f:
            data = json.load(f)
        if chat_name not in data:
            return []
        raw_message_data = data[chat_name][-limit:]
        whatsapp_messages = [WhatsAppMessage(
            sender="You" if m["is_outgoing"] else chat_name,
            content=m["content"],
            timestamp=datetime.fromisoformat(m["timestamp"]),
            is_outgoing=m["is_outgoing"],
            chat_name=chat_name,
        ) for m in raw_message_data]
        return whatsapp_messages

    def get_new_messages(self, chat_name: str, new_messages: list[WhatsAppMessage], after_last_outgoing: bool = False) -> list[WhatsAppMessage]:
        old_messages = self.get_seen_messages(chat_name)
        old_message_keys = [(m.content, m.timestamp, m.is_outgoing) for m in old_messages]
        new_messages = [m for m in new_messages if (m.content, m.timestamp, m.is_outgoing) not in old_message_keys]
        if after_last_outgoing:
            outgoing_indices = [i for i, m in enumerate(new_messages) if m.is_outgoing]
            if outgoing_indices:
                last_outgoing_index = outgoing_indices[-1]
                return new_messages[last_outgoing_index+1:]
        return new_messages


def dedupe_messages(messages: list[MessageLog]) -> list[MessageLog]:
    seen = set()
    out = []
    for message in messages:
        key = (message["content"], message["timestamp"], message["is_outgoing"])
        if key in seen:
            continue
        seen.add(key)
        out.append(message)
    return out