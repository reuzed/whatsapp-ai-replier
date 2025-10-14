from typing import List
from src.schemas import WhatsAppMessage, ChatAction, ReactChatAction, Chatter

from datetime import datetime, timedelta

class ReactChatter(Chatter):
    def __init__(self, emoji_name: str):
        self.emoji_name = emoji_name

    def on_receive_messages(self, messages: List[WhatsAppMessage]) -> List[ChatAction]:
        return [ReactChatAction(message=messages[0], timestamp=datetime.now(), emoji_name=self.emoji_name)]
