from src.schemas import WhatsAppMessage, ChatAction
from src.llm_client import LLMManager
from datetime import datetime

class SimpleAIChatter:
    def __init__(self):
        self.llm_manager = LLMManager()

    def on_receive_message(self, messages: list[WhatsAppMessage]) -> ChatAction:
        response = self.llm_manager.generate_whatsapp_response(messages)
        return ChatAction(message=response, timestamp=datetime.now())