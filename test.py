import asyncio
from whatsapp_automation import WhatsAppAutomation
from logging import getLogger
logger = getLogger("")

def manual_message() -> None:
    """Manually message somebody using the api"""
    automation = WhatsAppAutomation()

    asyncio.run(automation.start())
    
    chat_name = "Matthew" # input("Who do you want to chat to?")
    
    print(f"Trying to select chat '{chat_name}'")    
    
    print(automation.select_chat(chat_name))
    
    msgs = automation.get_recent_messages(5)
    for msg in msgs:
        print(f"{msg.sender}: {msg.content}")
        
    response = input(">")
    
    if automation.send_message(response):
        print("Replied to message at %s", msg.timestamp.strftime("%H:%M:%S"))
    
if __name__ == "__main__":
    #manual_message()
    """Manually message somebody using the api"""
    automation = WhatsAppAutomation()

    asyncio.run(automation.start())
    
    print(automation.list_chat_names())
    
    print(f"Trying to select chat 'Matthew")    
    
    print(automation.select_chat("Matthew"))
    
    print(automation.select_chat("Ben Blaker"))
    
    print(automation.list_chat_names())
    
    msgs = automation.get_recent_messages(5)
    for msg in msgs:
        print(f"{msg.sender}: {msg.content}")
        
    response = input(">")
    
    if automation.send_message(response):
        print("Replied to message at %s", msg.timestamp.strftime("%H:%M:%S"))
    