import asyncio
import time
from datetime import datetime
import os

from dotenv import load_dotenv

from src.whatsapp_automation import WhatsAppAutomation
from src.actions_handler import ActionsHandler
from src.schemas import ImageChatAction


def main():
    load_dotenv()
    friend = os.getenv("FRIEND_NAME", "Reuben")
    prompt = os.getenv("IMAGE_PROMPT", "A photorealistic picture of playful dogs in a park")
    model = os.getenv("IMAGE_MODEL", "dall-e-3")

    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    actions = ActionsHandler(automation)

    # Ensure chat open
    automation.select_chat(friend)
    time.sleep(2)

    # Construct action and handle it immediately
    action = ImageChatAction(
        prompt=prompt,
        chat_name=friend,
        timestamp=datetime.now(),
        n=1,
        model=model,
        output_filename="test_chat_actions_image",
    )

    remaining = actions.handle_actions([action], friend=friend)
    print(f"Remaining actions: {remaining}")

    # Give time for send flow to complete
    input("Press Enter to quit...")


if __name__ == "__main__":
    main()


