from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class WhatsAppMessage:
    """Represents a WhatsApp message."""
    sender: str
    content: str
    timestamp: datetime
    is_outgoing: bool
    chat_name: str
    def __hash__(self):
        return hash((self.sender, self.content, self.timestamp, self.is_outgoing, self.chat_name))

@dataclass
class ChatState:
    text: str
    last_message: Optional[WhatsAppMessage]
    
@dataclass
class ChatListEntry:
    name: str
    preview: str
    time_text: str
    
@dataclass
class ChatAction:
    message: WhatsAppMessage
    timestamp: datetime

class Chatter:
    def __init__(self, *args, **kwargs):
        pass
    
    def on_receive_messages(self, messages: list[WhatsAppMessage]) -> ChatAction:
        pass
    
