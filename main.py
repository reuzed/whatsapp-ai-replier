import asyncio
from src.whatsapp_automation import WhatsAppAutomation
import time

def main():
    print("Hello from whatsapp-ai-replier!")


if __name__ == "__main__":
    whatsapp_automation = WhatsAppAutomation()
    asyncio.run(whatsapp_automation.start())
    
    time.sleep(1)
    chat_name = "Ben Blaker"
    whatsapp_automation.select_chat(chat_name)
    time.sleep(1)
    
    # whatsapp_automation.react_to_latest_incoming("clown")
    whatsapp_automation.react_to_message_containing("Truben", "laugh")
    input("Press Enter to quit")
