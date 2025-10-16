from typing import List
from src.schemas import WhatsAppMessage, ChatAction, ReactAction, Chatter, Action

from datetime import datetime, timedelta

class ReactChatter(Chatter):
    def __init__(self, emoji_name: str):
        self.emoji_name = emoji_name

    def on_receive_messages(self, messages: List[WhatsAppMessage], chat_name: str) -> List[ReactAction]:
        return [ReactAction(message_to_react=messages[0], timestamp=datetime.now(), emoji_name=self.emoji_name)]
