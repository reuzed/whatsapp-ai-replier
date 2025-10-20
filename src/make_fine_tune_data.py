import json
from pathlib import Path
from src.llm_client import LLMManager
import asyncio

FINE_TUNE_DATA_DIR = Path(__file__).parent.parent

class FineTuningDataManager():
    def __init__(self):
        self.llm_manager = LLMManager()

    async def create_fine_tune_data(self, conv_file: str):
        """Create somewhat syntheticfine-tune data file from a conversation file.
        Make this by extracting actual messages from a user, and put them through an LLM to generate a pair of (LLM message, user message).
        Save this to a file for use in fine-tuning for style."""
        with open(conv_file, "r") as f:
            conv = json.load(f)
        user_message_set = set()
        message_data = conv["messages"]
        for message in message_data:
            if message["is_outgoing"]:
                user_message_set.add(message["content"])
        user_messages = list(user_message_set)
        llm_message_tasks = []
        for user_message in user_messages:
            llm_message_task = asyncio.create_task(self.generate_llm_user_message_pair(user_message))
            llm_message_tasks.append(llm_message_task)
        llm_user_pairs = await asyncio.gather(*llm_message_tasks)
        file_name = "fine_tune_data.json"
        file_address = FINE_TUNE_DATA_DIR / "fine_tuning_data" / file_name
        with open(file_address, "w") as f:
            json.dump(llm_user_pairs, f, indent=4)

    async def generate_llm_user_message_pair(self, user_message: str) -> dict: # adjust this from being a dummy function
        messages = [{"role": "user", "content": user_message}]
        system_prompt = "" # TODO: create this system prompt using the user's style guide, etc
        llm_response = await self.llm_manager.generate_response(messages, system_prompt=system_prompt, allow_skip=False)
        return {"llm_message": llm_response.text, "user_message": user_message}

if __name__ == "__main__":
    fine_tuning_data_manager = FineTuningDataManager()
    conv_data_file = "conversations/723_20251020_152750.json"
    asyncio.run(fine_tuning_data_manager.create_fine_tune_data(conv_data_file))
