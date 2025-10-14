# Manage multiple chats within an event loop
# We need to cycle through the chats and read the messages in each chat
# Upon receiving a message, we need to decide what to do with it

from src.schemas import Chatter, ChatAction, WhatsAppMessage
import asyncio
from datetime import datetime
from src.whatsapp_automation import WhatsAppAutomation

# Import chatters
from src.chatters.trivial_chatter import TrivialChatter, DelayedTrivialChatter
from src.chatters.simple_ai_chatter import SimpleAIChatter
from src.chatters.chate_statter import ChateStatter

import time
from rich import print

def multi_event_loop(chat_names: list[str], chatters: list[Chatter]):
    # seen messages for each chat
    seen_message_contents = {chat_name: set() for chat_name in chat_names}
    # messages to be sent
    chat_actions = {chat_name: [] for chat_name in chat_names}
    # init automation
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    # seen message contents for each chat
    for chat_name in chat_names:
        automation.select_chat(chat_name)
        print(f"[orange]Selected chat[/orange] {chat_name}")
        time.sleep(1)
        # mark messages in chat as seen
        start_messages = automation.get_visible_messages_simple(10)
        for message in start_messages:
            seen_message_contents[chat_name].add(message.content)
        
    print(f"Marked {len(start_messages)} messages as seen")
    print("[yellow]Seen message contents:[/yellow]")
    print("\n", seen_message_contents, "\n")
    
    looping = True
    while looping:
        time.sleep(5)
        for chat_name in chat_names:
            automation.select_chat(chat_name)
            print(f"[orange]Selected chat[/orange] {chat_name}")
            time.sleep(1)
        
            # get recent messages
            messages = automation.get_visible_messages_simple(5)
            for message in messages:
                if message.is_outgoing or message.content in seen_message_contents[chat_name]:
                    continue
                print("[green]Found new message[/green]")
                print(f"\nFrom {message.sender}: {message.content}\n")
                
                seen_message_contents[chat_name].add(message.content)
                actions = chatters[chat_names.index(chat_name)].on_receive_messages([message])
                print("[blue]Chatter has decided on the following actions:[/blue]")
                print(actions)
                print("\n")
                    
                chat_actions.extend(actions)
        
        now = datetime.now()
        to_remove = []
        for action in chat_actions:
            if now > action.timestamp:
                if isinstance(action, ChatAction):
                    print(f"[red]Sending message:[/red]")
                    print(f"\n{action.message.content}\n")
                    automation.send_message(action.message.content)
                    to_remove.append(action)
                elif isinstance(action, ReactAction):
                    print(f"[red]Reacting with[/red] {action.emoji_name} [red]to[/red] {action.message_to_react.content}")
                    automation.react_to_message(action.message_to_react.content, action.emoji_name)
                    to_remove.append(action)
                else:
                    print(f"[red]Unknown action type:[/red] {action}")
        for action in to_remove:
            chat_actions.remove(action)

if __name__ == "__main__":
    """Event loop for multiple chats"""
    if input("Type something to manually set up the event loop, or return to use some defaults."):
        chat_names = input("Enter chat names separated by commas: ").split(",")
        chatters = [Chat(user_name, chat_name) for chat_name in chat_names]
    else:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        chat_names = os.getenv("MULTI_EVENT_LOOP_CHAT_NAMES", "Reuben,Matthew,Ben").split(",")
        chatters = [Chat(user_name, chat_name) for chat_name in chat_names]
    
    event_loop(chat_names, chatters)