from src.schemas import Chatter, ChatAction, WhatsAppMessage, ReactAction
import asyncio
from datetime import datetime
from src.whatsapp_automation import WhatsAppAutomation

# Import chatters
from src.chatters.trivial_chatter import TrivialChatter, DelayedTrivialChatter
from src.chatters.simple_ai_chatter import SimpleAIChatter
from src.chatters.chate_statter import ChateStatter
from src.chatters.react_chatter import ReactChatter

import time
from rich import print

def event_loop(chat_name: str, chatter: Chatter):
    # messages already handled
    # seen_messages = set()
    seen_message_contents = set()
    # messages to be sent
    chat_actions = []
    
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    
    automation.select_chat(chat_name)
    print(f"Selected chat {chat_name}")
    
    # mark messages in chat as seen
    start_messages = automation.get_visible_messages_simple(10)
    for message in start_messages:
        # seen_messages.add(message)
        seen_message_contents.add(message.content)
        
    print(f"Marked {len(start_messages)} messages as seen")
    print("[yellow]Seen message contents:[/yellow]")
    print(f"\n{seen_message_contents}\n")
    
    while True:
        time.sleep(5)
        
        # get recent messages
        messages = automation.get_visible_messages_simple(5)
        for message in messages:
            if message.is_outgoing:
                # print(f"Skipping outgoing message from {message.sender}: {message.content}")
                continue
            if message.content in seen_message_contents:
                # print(f"Skipping seen message from {message.sender}: {message.content}")
                continue
            
            # print(messages)
            
            print("[green]Found new message[/green]")
            print(f"\nFrom {message.sender}: {message.content}\n")
            
            seen_message_contents.add(message.content)
            actions = chatter.on_receive_messages([message])
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
                    print(action)
                    automation.react_to_message(emoji_query=action.emoji_name, text_contains=action.message_to_react.content, )
                    to_remove.append(action)
                else:
                    print(f"[red]Unknown action type:[/red] {action}")
        for action in to_remove:
            chat_actions.remove(action)


def event_loop_develop(friend_list: str | list[str], chatter: Chatter):
    if isinstance(friend_list, str):
        friend_list = [friend_list]
    automation = WhatsAppAutomation()
    while True:
        for friend in friend_list:
            automation.select_chat(friend)
            time.sleep(1)
            process_friend(friend, chatter, automation)
            time.sleep(3)

def process_friend(friend: str, chatter: Chatter, automation: WhatsAppAutomation):
    print("Not implemented friend processing yet")
    pass



if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    
    if not input("Manually control chatter? (return for env variables)"):
        load_dotenv()
        friend_name = os.getenv("FRIEND_NAME", "Reuben")
        user_name = os.getenv("USER_NAME", "Ben")
        chatter = ChateStatter(user_name, friend_name)
        event_loop(friend_name, chatter)
    else:
        friend_name = input("Name of friend to chat to")
        user_name = os.getenv("USER_NAME", "Ben")
        chatter_name = input("Name of chatter to use (t, dt, sai, cs, rc)")
        if chatter_name == "t":
            chatter = TrivialChatter()
        elif chatter_name == "dt":
            chatter = DelayedTrivialChatter()
        elif chatter_name == "sai":
            chatter = SimpleAIChatter()
        elif chatter_name == "cs":
            chatter = ChateStatter(user_name, friend_name)
        else:
            #chatter_name == "rc":
            chatter = ReactChatter(input("Emoji name to react with"))
        event_loop(friend_name, chatter)