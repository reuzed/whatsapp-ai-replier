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

def run_manual_loop() -> None:
    """Run a manual loop to send messages to a chat"""
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    
    print("Type q to quit, l to list chats, c to select a chat")
    # when in a chat q should quit back to choose chat, l should have optional search term after space
    # c should ask on the next line for chat name
    mode = "menu"
    while True:
        prompt = "Type q to quit, l to list chats, c to select a chat" if mode == "menu" else ">"
        response = input(prompt)
        if mode == "menu":
            if response == "q":
                break
            elif response[0] == "l":
                print(automation.list_chat_names(search_term=response[2:]))
            elif response == "c":
                print(automation.select_chat(input("Chat name: ")))
                mode = "chat"
        elif mode == "chat":
            if response == "q":
                mode = "menu"
            else:
                success = automation.send_message(response)
                if success:
                    print("Replied to message successfully")
                else:
                    print("Failed to reply to message")

if __name__ == "__main__":
    #manual_message()
    """Manually message somebody using the api"""
    
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
        
    while True:
        k = input("Press Enter to continue, sc to scroll chat list, s to scroll chat")
        if k == "sc":
            print(automation.scroll_chat_list("up"))
        elif k == "s":
            print(automation.scroll_chat("up"))
        elif k == "scp":
            print(automation.scroll_chat_list("down"))
        elif k == "sp":
            print(automation.scroll_chat("down"))
        else:
            msgs = automation.get_visible_messages_simple(50)
            for msg in msgs:
                print(f"{msg.sender}: {msg.content} - {msg.timestamp.strftime('%H:%M:%S')}")