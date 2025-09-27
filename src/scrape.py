import asyncio
import time
from src.whatsapp_automation import WhatsAppAutomation

class Scraper:
    def __init__(self):
        self.whatsapp_automation = WhatsAppAutomation()
        asyncio.run(self.whatsapp_automation.start())
    
    def scrape_chat(self, chat_name: str):
        self.whatsapp_automation.select_chat(chat_name)
        time.sleep(0.5)
        messages = set()
        
        for i in range(10):
            new_messages = self.whatsapp_automation.get_visible_messages_simple(50)
            for new_message in new_messages:
                if new_message not in messages:
                    messages.add(new_message)
            time.sleep(0.5)
            self.whatsapp_automation.scroll_chat("down")
            time.sleep(0.5)
            
        return messages
    
if __name__ == "__main__":
    scraper = Scraper()
    messages = scraper.scrape_chat("Ben Blaker")
    print(len(messages))
    for message in messages:
        print(message.sender, message.content)