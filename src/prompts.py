from src.schemas import WhatsAppMessage

STATE_UPDATER_SYSTEM_PROMPT_TEMPLATE = """You are an assistant representing {user_name} tasked with keeping track of key facts about a {friend_name}.
Based on the new messages, only update long term state tracking if there has been new important information about the person.
If facts are date dependent include specific day or time references.
"""

def create_state_updater_prompts(user_name:str, friend_name:str, prev_state_text: str, current_date: str, new_messages: list[WhatsAppMessage]) -> tuple[str, str]:
    system_prompt = f"The current date is {current_date}. " + STATE_UPDATER_SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name, friend_name=friend_name) + "\n"
    system_prompt += f"<current_state>{prev_state_text}</current_state>\n"
    system_prompt += f"<new_messages>{_map_messages_to_str(new_messages)}</new_messages>"
    user = f"Now return a concise updated state, without any additional commentary."
    return system_prompt, user

def _map_messages_to_str(messages: list[WhatsAppMessage]) -> str:
    return "\n".join([_map_message_to_str(m) for m in messages])

def _map_message_to_str(msg: WhatsAppMessage) -> str:
    timestamp = msg.timestamp.isoformat() if msg.timestamp else "Unknown time"
    return f"[{timestamp}] {msg.sender}: {msg.content}"

REPLIER_SYSTEM_PROMPT_TEMPLATE = "You are an assistant continuing a conversation between {user_name} and {friend_name} on behalf of {user_name}. Use lower case, typos, slang, and emojis to match gen z style and be undetectable as an AI."

def create_replier_system_prompt(user_name:str, friend_name:str, state_text: str, current_date: str) -> str:
    system_prompt = f"The current date is {current_date}. " + REPLIER_SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name, friend_name=friend_name) + f"<key_facts>{state_text}</key_facts>"
    return system_prompt

REACTER_SYSTEM_PROMPT_TEMPLATE = "You are an assistant in a conversation between {user_name} and {friend_name} on behalf of {user_name}. Decide whether to use react tool for any message in message history, specifying the message to react to and desired emoji, or otherwise skip."

def create_reacter_system_prompt(user_name:str, friend_name:str, state_text: str, current_date: str) -> str:
    system_prompt = f"The current date is {current_date}. " + REACTER_SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name, friend_name=friend_name) + f"<key_facts>{state_text}</key_facts>"
    return system_prompt