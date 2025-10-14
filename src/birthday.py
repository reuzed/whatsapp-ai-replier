"""Send somebody a birthday message"""

from src.whatsapp_automation import WhatsAppAutomation
import asyncio
from src.llm_client import LLMManager
import time

def send_birthday_message(chat_name: str, friend_name: str | None = None, check: bool = False):
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    automation.select_chat(chat_name)
    
    llm_manager = LLMManager()
    if not friend_name:
        friend_name = chat_name
    response = asyncio.run(llm_manager.generate_response(
        [
            {
                "role": "user",
                "content": """You are a friendly birthday message geenerator.
                You use emoji, gen z type slang, and do not use any ai phrases.
                You send short kind sweet messages that a friend might send.
                Reply only with the message you would send.
                A basic example is 'Happy birthday! 🎉 hope you have a great day :)'""" + (
                    f"Generate a birthday message for my friend {friend_name}'s birthday"
                )
            },
        ]
    ))
    if check:
        if input("Is this message ok? " + response + "Press y to send, n to deny") == "y":
            automation.send_message(response)
            time.sleep(1)
        else:
            print("Message denied")
    else:
        automation.send_message(response)

if __name__ == "__main__":
    send_birthday_message("Reu")