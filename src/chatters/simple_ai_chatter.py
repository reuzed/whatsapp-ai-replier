from typing import List
from src.schemas import WhatsAppMessage, ChatAction, Chatter
from src.llm_client import LLMManager
from datetime import datetime

class SimpleAIChatter(Chatter):
    def __init__(self):
        self.llm_manager = LLMManager()

    def on_receive_messages(self, messages: List[WhatsAppMessage], chat_name: str) -> List[ChatAction]:
        response_message = self.llm_manager.generate_whatsapp_chatter_response(messages)
        return [ChatAction(message=response_message, timestamp=datetime.now())]