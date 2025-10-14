from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from abc import ABC, abstractmethod

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

class Chatter(ABC):
    @abstractmethod
    def on_receive_messages(self, messages: List[WhatsAppMessage]) -> List[ChatAction]:
        pass
    
