"""Send somebody a birthday message"""

from whatsapp_automation import WhatsAppAutomation
import asyncio
from llm_client import LLMManager

def send_birthday_message(chat_name: str):
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    automation.select_chat(chat_name)
    
    llm_manager = LLMManager()
    response = asyncio.run(llm_manager.generate_response(
        [
            {
                "role": "user",
                "content": """You are a friendly birthday message geenerator.
                You use emoji, gen z type slang, and do not use any ai phrases.
                You send short kind sweet messages that a frinnd might send.
                Reply only with the message you would send.
                A basic example is 'Happy birthday! 🎉 hope you have a great day xx :)'""" + (
                    "Generate a birthday message for my friend Jess's birthday, she's 24 years old"
                )
            },
        ]
    ))
    # input(response)
    automation.send_message(response)
    input("Press Enter to quit")

if __name__ == "__main__":
    send_birthday_message("Jess")