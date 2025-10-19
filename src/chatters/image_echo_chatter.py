from typing import List
from datetime import datetime
from random import choice       
from src.schemas import WhatsAppMessage, Chatter, ImageChatAction, Action, GifChatAction

class ImageEchoChatter(Chatter):
    def __init__(self, model: str | None = None):
        self.model = model

    def on_receive_messages(self, messages: List[WhatsAppMessage], chat_name: str) -> List[Action]:
        latest = messages[-1]
        # Echo the user's message as the image generation prompt or gif search term, randomly choose one
        if choice([True, False]):
            return [
                ImageChatAction(
                    prompt=latest.content,
                    chat_name=chat_name,
                    timestamp=datetime.now(),
                    n=1,
                    model=self.model,
                    output_filename="image_echo_test",
                )
            ]
        else:
            return [
                GifChatAction(
                    search_term=latest.content,
                    chat_name=chat_name,
                    timestamp=datetime.now(),
                    press_enter_to_send=True,
                )
            ]


