from typing import List
from src.schemas import WhatsAppMessage, ChatAction, ReactAction, Chatter, Action

from datetime import datetime, timedelta

class AutoClown(Chatter):
    def __init__(self, emoji_name: str = "clown"):
        self.emoji_name = emoji_name

    async def on_receive_messages(self, messages: List[WhatsAppMessage], chat_name: str) -> List[Action]:
        actions: List[Action] = []
        # React to the most recent incoming message (if any)
        incoming = [m for m in messages if not m.is_outgoing]
        if incoming:
            target = incoming[-1]
            actions.append(ReactAction(message_to_react=target, timestamp=datetime.now(), emoji_name=self.emoji_name))
        # Always send the potato message
        outgoing = WhatsAppMessage(
            sender="You",
            content="You are a potato!",
            timestamp=datetime.now(),
            is_outgoing=True,
            chat_name=chat_name,
        )
        actions.append(ChatAction(message=outgoing, timestamp=datetime.now()))
        return actions
