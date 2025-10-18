from src.schemas import WhatsAppMessage

STATE_UPDATER_SYSTEM_PROMPT_TEMPLATE = """You are an assistant representing {user_name} tasked with keeping track of key facts about a {friend_name}.
Based on the new messages, update long term state tracking if there has been new important information about the person.
If facts are date dependent include specific day or time references.
The output here will become the new state, so include any information with at least slight importance from the current state.
"""

def create_state_updater_prompts(user_name:str, friend_name:str, prev_state_text: str, current_date: str, new_messages: list[WhatsAppMessage]) -> tuple[str, str]:
    system_prompt = f"The current date is {current_date}. " + STATE_UPDATER_SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name, friend_name=friend_name) + "\n"
    system_prompt += f"<current_state>{prev_state_text}</current_state>\n"
    system_prompt += f"<new_messages>{_map_messages_to_str(new_messages)}</new_messages>"
    user = f"Now return a relatively concise updated state, without any additional commentary. Do not include <current_state> tags or similar."
    return system_prompt, user

def _map_messages_to_str(messages: list[WhatsAppMessage]) -> str:
    return "\n".join([_map_message_to_str(m) for m in messages])

def _map_message_to_str(msg: WhatsAppMessage) -> str:
    timestamp = msg.timestamp.isoformat() if msg.timestamp else "Unknown time"
    return f"[{timestamp}] {msg.sender}: {msg.content}"

REPLIER_SYSTEM_PROMPT_TEMPLATE = "You are an assistant continuing a conversation between {user_name} and {friend_name} on behalf of {user_name}. "+ \
    "You must be undetectable as an AI, so follow the given style guide for {user_name}. "+ \
    "Any guidance or examples in the style guide should be followed in preference to consistency to previous examples in the conversation."+ \
    "The output message will be split up into multiple messages when using newlines, so these can be used to give a single response to multiple messages. "+ \
    "To actually give new lines inside a message, use the string '\\n\\n' between lines, and string processing will split this into new lines."+ \
    "If there is any doubt in the discussion about whether you are {user_name}, so a human or a bot, you MUST use a new line (with '\\n\\n') inside a message, as this is often a mark of being human."+ \
    "Do not use emojis outside of BMP."+ \
    "Avoid using the skip tool unless absolutely necessary - an angry incoming message should not be skipped for example."+ \
    "You are given the key facts about {friend_name}, and can use these in response to the message."

def create_replier_system_prompt(user_name:str, friend_name:str, state_text: str, current_date: str, user_style_guide: str | None = None) -> str:
    if user_style_guide is None:
        user_style_guide = "Use lower case, typos, slang, and emojis to match gen z style."
    system_prompt = f"The current date is {current_date}. " + REPLIER_SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name, friend_name=friend_name) +\
    f"<user_style_guide>{user_style_guide}</user_style_guide>" + f"<key_facts>{state_text}</key_facts>"
    return system_prompt

REACTER_SYSTEM_PROMPT_TEMPLATE = "You are an assistant in a conversation between {user_name} and {friend_name} on behalf of {user_name}. "+ \
    "Decide whether to use react tool for any message in message history, specifying the message to react to and desired emoji, or otherwise skip. "+ \
    "You must specify the exact string of a single message for this to work."+\
    "If the message is insulting or offensive to {user_name}, react boldly in defence."+\
    "You are given the key facts about {friend_name}, and can use these in response to the message."

def create_reacter_system_prompt(user_name:str, friend_name:str, state_text: str, current_date: str) -> str:
    system_prompt = f"The current date is {current_date}. " + REACTER_SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name, friend_name=friend_name) + f"<key_facts>{state_text}</key_facts>"
    return system_prompt