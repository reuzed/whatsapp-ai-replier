from src.schemas import Chatter, ChatAction, WhatsAppMessage
import asyncio
from datetime import datetime
from src.whatsapp_automation import WhatsAppAutomation

# Import chatters
from src.chatters.trivial_chatter import TrivialChatter, DelayedTrivialChatter
from src.chatters.simple_ai_chatter import SimpleAIChatter

import time
from rich import print

def event_loop(chat_name: str, chatter: Chatter):
    # messages already handled
    seen_messages = set()
    # messages to be sent
    chat_actions = []
    
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    
    automation.select_chat(chat_name)
    print(f"Selected chat {chat_name}")
    
    # mark messages in chat as seen
    start_messages = automation.get_visible_messages_simple(10)
    for message in start_messages:
        seen_messages.add(message)
        
    print(f"Marked {len(start_messages)} messages as seen")
    
    while True:
        time.sleep(5)
        
        # get recent messages
        messages = automation.get_visible_messages_simple(5)
        for message in messages:
            if message.is_outgoing:
                print(f"Skipping outgoing message from {message.sender}: {message.content}")
                continue
            if message in seen_messages:
                print(f"Skipping seen message from {message.sender}: {message.content}")
                continue
            
            print(messages)
            print(f"Found new message from {message.sender}: {message.content}")
            seen_messages.add(message)
            action = chatter.on_receive_messages([message])
            chat_actions.append(action)
        
        now = datetime.now()
        to_remove = []
        for action in chat_actions:
            if now > action.timestamp:
                print(f"Sending message: {action.message.content}")
                automation.send_message(action.message.content)
                to_remove.append(action)
        for action in to_remove:
            chat_actions.remove(action)

if __name__ == "__main__":
    chatter = SimpleAIChatter()
    chat_name = "Ben Blaker"
    event_loop(chat_name, chatter)