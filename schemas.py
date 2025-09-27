from dataclasses import dataclass
import datetime

@dataclass
class WhatsAppMessage:
    """Represents a WhatsApp message."""
    sender: str
    content: str
    timestamp: datetime
    is_outgoing: bool
    chat_name: str

@dataclass
class ChatState:
    text: str
    last_message: WhatsAppMessage