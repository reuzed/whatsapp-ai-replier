from schemas import WhatsAppMessage
from chat import Chat
from datetime import datetime

sample_messages = [
    WhatsAppMessage(
        sender="Alice",
        content="Hey, how's it going?",
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
    import asyncio
    chat = Chat("Alice", "Bob")
    chat._reset_state()  # Reset state before testing
    response, send_after = asyncio.run(chat.on_messages_received(sample_messages))
    print(f"Response: {response}, Send after: {send_after}")