from src.whatsapp_automation import WhatsAppAutomation
from src.llm_client import LLMManager
import asyncio
import time

def prompt_to_message(chat_name: str,  prompt: str) -> str | None:
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    automation.select_chat(chat_name)
    time.sleep(1)
    response = asyncio.run(LLMManager().complete_message(
        prompt, 
        system= ("You are an AI model you will follow the instructions or content of the following prompt and "
                "return only a sensible whatsapp message. Use friendly casual human speak of talking amongst friends."
                "Only output the message, no other text."
                "Use the prompt as a guide and use your intuition to figure out what message is trying to be sent"
                ),
    ))

    if input("Is this message ok? " + response + "Press y to send, n to deny") == "y":
        automation.send_message(response)
        time.sleep(1)
        return response
    else:
        print("Message denied")
        return None

if __name__ == "__main__":
    chat_name = input("Choose chat: ")
    prompt_to_message(chat_name, input("Enter prompt: "))
    input("Press Enter to quit")