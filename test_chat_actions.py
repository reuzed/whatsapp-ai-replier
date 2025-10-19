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
    # Interactive prompts with env-backed defaults
    default_friend = os.getenv("FRIEND_NAME", "Reuben")
    default_prompt = os.getenv("IMAGE_PROMPT", "A photorealistic picture of playful dogs in a park")
    default_model = os.getenv("IMAGE_MODEL", "dall-e-3")

    try:
        friend = input(f"Friend/chat name [{default_friend}]: ").strip() or default_friend
        prompt = input(f"Image prompt [{default_prompt}]: ").strip() or default_prompt
        model = input(f"Image model [{default_model}]: ").strip() or default_model
    except (EOFError, KeyboardInterrupt):
        print("Aborted")
        return

    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    actions = ActionsHandler(automation)

    # Ensure chat open
    automation.select_chat(friend)
    time.sleep(1)

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


