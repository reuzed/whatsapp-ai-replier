from schemas import WhatsAppMessage

STATE_UPDATER_SYSTEM_PROMPT_TEMPLATE = """You are an assistant tasked with keeping track of key facts about a WhatsApp chat.
Based on the new messages, only update long term state tracking if there has been new important information.
If facts are date dependent include specific day or time references.
"""

def create_state_updater_prompts(prev_state_text: str, current_date: str, new_messages: list[WhatsAppMessage]) -> tuple[str, str]:
    system_prompt = f"The current date is {current_date}. " + STATE_UPDATER_SYSTEM_PROMPT_TEMPLATE
    system_prompt += f"<current_state>{prev_state_text}</current_state>\n"
    system_prompt += f"<new_messages>{_map_messages_to_str(new_messages)}</new_messages>"
    user = f"Now return an updated state, or the same state if nothing has changed. Only return the updated state text, without any additional commentary."
    return system_prompt, user

def _map_messages_to_str(messages: list[WhatsAppMessage]) -> str:
    return "\n".join([_map_message_to_str(m) for m in messages])

def _map_message_to_str(msg: WhatsAppMessage) -> str:
    timestamp = msg.timestamp.isoformat() if msg.timestamp else "Unknown time"
    return f"[{timestamp}] {msg.sender}: {msg.content}"

REPLIER_SYSTEM_PROMPT_TEMPLATE = """Reply to the following WhatsApp messages in the style of the receiver."""

def create_replier_system_prompt(state_text: str, current_date: str) -> str:
    system_prompt = f"The current date is {current_date}. " + REPLIER_SYSTEM_PROMPT_TEMPLATE + f"<current_state>{state_text}</current_state>"
    return system_prompt