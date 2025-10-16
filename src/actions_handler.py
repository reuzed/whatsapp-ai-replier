from datetime import datetime
from src.schemas import Action, ChatAction, ReactAction
from src.whatsapp_automation import WhatsAppAutomation

class ActionsHandler:
    def __init__(self, automation: WhatsAppAutomation):
        self.automation = automation

    def handle_actions(self, chat_actions: list[Action]):
        now = datetime.now()
        for action in chat_actions:
            if now > action.timestamp:
                if isinstance(action, ChatAction):
                    print(f"[red]Sending message:[/red]")
                    print(f"\n{action.message.content}\n")
                    self.automation.send_message(action.message.content)
                elif isinstance(action, ReactAction):
                    print(f"[red]Reacting with[/red] {action.emoji_name} [red]to[/red] {action.message_to_react.content}")
                    print(action)
                    self.automation.react_to_message(emoji_query=action.emoji_name, text_contains=action.message_to_react.content, )
                else:
                    print(f"[red]Unknown action type:[/red] {action}")
        # maybe add back in removing handled actions for error handling