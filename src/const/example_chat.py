from src.schemas import WhatsAppMessage
from src.chat import Chat
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
    chat = Chat("Alice", "Bob")
    chat._reset_state()  # Reset state before testing
    action = chat.on_receive_messages(sample_messages)[0] # this now returns a list of ChatAction, so take first
    print(f"Response: {action.message}, Send after: {action.timestamp}")