from src.schemas import WhatsAppMessage, ChatAction

from datetime import datetime, timedelta

class TrivialChatter:
    def __init__(self):
        pass

    def on_receive_message(self, messages: list[WhatsAppMessage]) -> ChatAction:
        return ChatAction(message=messages[0], timestamp=datetime.now())
    
class DelayedTrivialChatter:
    def __init__(self):
        pass

    def on_receive_message(self, messages: list[WhatsAppMessage]) -> ChatAction:
        return ChatAction(message=messages[0], timestamp=datetime.now() + timedelta(seconds=10))