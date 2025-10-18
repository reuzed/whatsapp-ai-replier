from datetime import datetime
from src.schemas import Action, ChatAction, ReactAction, WhatsAppMessage
from src.whatsapp_automation import WhatsAppAutomation
import time

class ActionsHandler:
    def __init__(self, automation: WhatsAppAutomation):
        self.automation = automation

    def handle_actions(self, chat_actions: list[Action], friend: str | None = None) -> list[Action]:
        now = datetime.now()
        to_remove = []
        if friend is not None:
            self.automation.select_chat(friend)
            time.sleep(2)
        split_chat_actions = []
        for action in chat_actions:
            if isinstance(action, ChatAction):
                split_chat_actions.extend(self._split_chat_action_into_multiple(action))
            else:
                split_chat_actions.append(action)
        chat_actions = split_chat_actions

        for action in chat_actions:
            if now > action.timestamp:
                if isinstance(action, ChatAction):
                    print(f"[red]Sending message:[/red]")
                    print(f"\n{action.message.content}\n")
                    if friend is None:
                        self.automation.select_chat(action.message.chat_name)
                        time.sleep(2)
                    self.automation.send_message(action.message.content)
                    to_remove.append(action)
                elif isinstance(action, ReactAction):
                    print(f"[red]Reacting with[/red] {action.emoji_name} [red]to[/red] {action.message_to_react.content}")
                    print(action)
                    if friend is None:
                        self.automation.select_chat(action.message_to_react.chat_name)
                        time.sleep(2)
                    self.automation.react_to_message(emoji_query=action.emoji_name, text_contains=action.message_to_react.content, )
                    to_remove.append(action)
                else:
                    print(f"[red]Unknown action type:[/red] {action}")
        # this allows for actions to be done in later future
        for action in to_remove:
            chat_actions.remove(action)
        return chat_actions

    def _split_chat_action_into_multiple(self, chat_action: ChatAction) -> list[ChatAction]:
        messages = chat_action.message.content.split("\n\n")
        messages = [message.replace("\\n\\n", "\n\n") for message in messages]
        new_chat_actions = []
        for i, message in enumerate(messages):
            new_message = WhatsAppMessage(sender=chat_action.message.sender, content=message, timestamp=chat_action.timestamp, is_outgoing=chat_action.message.is_outgoing, chat_name=chat_action.message.chat_name)
            new_chat_actions.append(ChatAction(message=new_message, timestamp=chat_action.timestamp))
        return new_chat_actions