STATE_UPDATER_SYSTEM_PROMPT_TEMPLATE = """You are an assistant tasked with keeping track of key facts about a WhatsApp chat.
Based on the new messages, only update long term state tracking if there has been new important information.
If facts are date dependent include specific day or time references.
"""

def create_state_updater_prompts(prev_state: str, current_date: str, chat_messages: str) -> str:
    system_prompt = f"The current date is {current_date}. " + STATE_UPDATER_SYSTEM_PROMPT_TEMPLATE + f"<current_state>{prev_state}</current_state>\n<new_messages>{chat_messages}</new_messages>"
    user = f"Now return an updated state, or the same state if nothing has changed. Only return the updated state text, without any additional commentary."
    return system_prompt, user