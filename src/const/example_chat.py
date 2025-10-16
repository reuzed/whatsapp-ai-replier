from src.schemas import WhatsAppMessage
from src.chatters.chate_statter import ChateStatter
from src.state_maintenance import StateMaintenance
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
    user_name = "Matthew"
    chat = ChateStatter(user_name)
    state_maintenance = StateMaintenance(user_name)
    state_maintenance.reset_state("Bob")  # Reset state before testing
    state_maintenance.reset_state("Alice")
    action = chat.on_receive_messages(sample_messages, "Bob")
    print(action)