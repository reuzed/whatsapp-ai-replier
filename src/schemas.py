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
        return hash((self.content, self.is_outgoing)) # this needs to be improved - and used more broadly


class MessageReaction:
    reactor: str
    reaction:str

class ImageContent:
    image_url: str

class GeneralWhatsappMessage:
    sender: str
    content: str | ImageContent
    timestamp: datetime
    is_outgoing: bool
    chat_name: str
    reactions: list[MessageReaction]
    


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

@dataclass
class ReactAction:
    message_to_react: WhatsAppMessage
    emoji_name: str
    timestamp: datetime

@dataclass
class ImageChatAction:
    prompt: str
    chat_name: str
    timestamp: datetime
    n: int = 1
    model: Optional[str] = None
    output_filename: Optional[str] = None

Action = ChatAction | ReactAction | ImageChatAction

class Chatter(ABC):
    @abstractmethod
    def on_receive_messages(self, messages: List[WhatsAppMessage], chat_name: str) -> List[Action]:
        pass