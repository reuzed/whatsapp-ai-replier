from src.schemas import Chatter, ChatAction, WhatsAppMessage, ReactAction, Action
import asyncio
from datetime import datetime
from src.whatsapp_automation import WhatsAppAutomation

# Import chatters
from src.chatters.frautomator import Frautomator
from src.chatters.autoClown import AutoClown
from src.state_maintenance import StateMaintenance
from src.actions_handler import ActionsHandler

import time

def event_loop(user_name: str, friend_list: list[str], chatter: Chatter):

    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    state_maintenance = StateMaintenance(user_name)
    actions_handler = ActionsHandler(automation)
    chat_actions = []

    if len(friend_list) == 1:
        chat_info = automation.select_chat(friend_list[0])
        time.sleep(1)

    while True:

        for friend in friend_list:

            if len(friend_list) > 1:
                chat_info = automation.select_chat(friend)
                time.sleep(1)

            chat_actions.extend(asyncio.run(process_friend(chat_info.chat_name, chatter, automation, state_maintenance)))

        chat_actions = actions_handler.handle_actions(chat_actions)

async def process_friend(friend: str, chatter: Chatter, automation: WhatsAppAutomation, state_maintenance: StateMaintenance) -> list[Action]:
    """Process a friend's messages and return actions, adding messages to message log.
    This is to respond to all new messages since last user message.
    The logging is done in this function only for message logging, not state, which is done by the chatter."""

    messages = automation.get_visible_messages_simple(20)
    new_messages = state_maintenance.get_new_messages(friend, messages)
    state_maintenance.log_seen_messages(messages)
    has_incoming = any(not m.is_outgoing for m in new_messages) # remove if wanting to store data about user messages in state or self reply

    if not has_incoming:
        friend_actions = []
    else:
        actions_task = asyncio.create_task(chatter.on_receive_messages(new_messages, friend))

        while not actions_task.done():
            await asyncio.sleep(0.5)
            messages = automation.get_visible_messages_simple(20)
            newer_messages = state_maintenance.get_new_messages(friend, messages)
            if newer_messages:
                actions_task.cancel()
                try:
                    await actions_task
                except asyncio.CancelledError:
                    pass
                actions_task = asyncio.create_task(chatter.on_receive_messages(newer_messages, friend))
                state_maintenance.log_seen_messages(messages)

        friend_actions = await actions_task

    return friend_actions


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    
    num_friends = int(input("Number of friends to chat to"))
    friend_names = []
    for i in range(num_friends):
        friend_names.append(input(f"Name of friend {i+1} to chat to"))
    user_name = os.getenv("USER_NAME", "Ben")
    chatter_name = input("Name of chatter to use (Frautomator, AutoClown): ")
    if chatter_name == "Frautomator":
        chatter = Frautomator(user_name)
    else:
        #chatter_name == "rc":
        chatter = AutoClown()
    event_loop(user_name, friend_names, chatter)