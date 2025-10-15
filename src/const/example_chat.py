from src.schemas import WhatsAppMessage
from src.chatters.chate_statter import ChateStatter
from datetime import datetime

sample_messages = [
    WhatsAppMessage(
        sender="Alice",
        content="hey how's it going",
        timestamp=datetime.now(),
        is_outgoing=True,
        chat_name="Alice"
    ),
    WhatsAppMessage(
        sender="Bob",
        content="I'm good, thanks! How about you?",
        timestamp=datetime.now(),
        is_outgoing=False,
        chat_name="Bob"
    )
]

if __name__ == "__main__":
    chat = ChateStatter("Alice", "Bob")
    chat._reset_state()  # Reset state before testing
    action = chat.on_receive_messages(sample_messages)
    print(action)