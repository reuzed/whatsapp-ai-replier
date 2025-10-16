from typing import List
from src.schemas import WhatsAppMessage, ChatAction, Chatter

from datetime import datetime, timedelta

class TrivialChatter(Chatter):
    def __init__(self):
        pass

    def on_receive_messages(self, messages: List[WhatsAppMessage], chat_name: str) -> List[ChatAction]:
        return [ChatAction(message=messages[0], timestamp=datetime.now())]
    
class DelayedTrivialChatter(Chatter):
    def __init__(self):
        pass

    def on_receive_messages(self, messages: List[WhatsAppMessage], chat_name: str) -> List[ChatAction]:
        return [ChatAction(message=messages[0], timestamp=datetime.now() + timedelta(seconds=10))]