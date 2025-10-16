from src.schemas import Chatter, ChatAction, WhatsAppMessage, ReactAction, Action
import asyncio
from datetime import datetime
from src.whatsapp_automation import WhatsAppAutomation

# Import chatters
from src.chatters.trivial_chatter import TrivialChatter, DelayedTrivialChatter
from src.chatters.simple_ai_chatter import SimpleAIChatter
from src.chatters.chate_statter import ChateStatter
from src.chatters.react_chatter import ReactChatter
from src.state_maintenance import StateMaintenance
from src.actions_handler import ActionsHandler

import time
from rich import print


def event_loop(user_name: str, friend_list: str | list[str], chatter: Chatter):
    if isinstance(friend_list, str):
        friend_list = [friend_list]
        single_friend = True
    else:
        single_friend = False
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    state_maintenance = StateMaintenance(user_name)
    actions_handler = ActionsHandler(automation)
    chat_actions = []
    if single_friend:
        automation.select_chat(friend_list[0])
        time.sleep(2)
    while True:
        for friend in friend_list:
            chat_actions.extend(process_friend(friend, chatter, automation, state_maintenance, single_friend=single_friend))
        chat_actions = actions_handler.handle_actions(chat_actions)

def process_friend(friend: str, chatter: Chatter, automation: WhatsAppAutomation, state_maintenance: StateMaintenance, single_friend: bool = False) -> list[Action]:
    """Process a friend's messages and return actions, adding messages to message log.
    This is to respond to all new messages since last user message.
    The logging is done in this function only for message logging, not state, which is done by the chatter."""
    if not single_friend:
        automation.select_chat(friend)
        time.sleep(2)
    messages = automation.get_visible_messages_simple(20)
    new_messages = state_maintenance.get_new_messages(friend, messages, after_last_outgoing=True)
    if len(new_messages) == 0:
        return []
    friend_actions = chatter.on_receive_messages(new_messages, friend)
    state_maintenance.log_seen_messages(messages)
    time.sleep(2)
    return friend_actions


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    
    if not input("Manually control chatter? (return for env variables)"):
        load_dotenv()
        friend_name = os.getenv("FRIEND_NAME", "Reuben")
        user_name = os.getenv("USER_NAME", "Ben")
        chatter = ChateStatter(user_name)
        event_loop(user_name, friend_name, chatter)
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
            chatter = ChateStatter(user_name)
        else:
            #chatter_name == "rc":
            chatter = ReactChatter(input("Emoji name to react with"))
        event_loop(user_name, friend_name, chatter)