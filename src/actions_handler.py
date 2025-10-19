from datetime import datetime
from src.schemas import Action, ChatAction, ReactAction, WhatsAppMessage, ImageChatAction, GifChatAction
from src.whatsapp_automation import WhatsAppAutomation
from src.image_gen import generate_image
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
                    self._handle_chat_action(action, friend)
                    to_remove.append(action)
                elif isinstance(action, ReactAction):
                    self._handle_react_action(action, friend)
                    to_remove.append(action)
                elif isinstance(action, ImageChatAction):
                    self._handle_image_chat_action(action, friend)
                    to_remove.append(action)
                elif isinstance(action, GifChatAction):
                    self._handle_gif_chat_action(action, friend)
                    to_remove.append(action)
                else:
                    print(f"[red]Unknown action type:[/red] {action}")
        # this allows for actions to be done in later future
        for action in to_remove:
            chat_actions.remove(action)
        return chat_actions

    def _split_chat_action_into_multiple(self, chat_action: ChatAction) -> list[ChatAction]:
        messages = chat_action.message.content.split("\n\n")
        messages = [message.replace("make_newline", "\n\n") for message in messages]
        new_chat_actions = []
        for i, message in enumerate(messages):
            new_message = WhatsAppMessage(sender=chat_action.message.sender, content=message, timestamp=chat_action.timestamp, is_outgoing=chat_action.message.is_outgoing, chat_name=chat_action.message.chat_name)
            new_chat_actions.append(ChatAction(message=new_message, timestamp=chat_action.timestamp))
        return new_chat_actions

    def _handle_chat_action(self, action: ChatAction, friend: str | None) -> None:
        print(f"[red]Sending message:[/red]")
        print(f"\n{action.message.content}\n")
        if friend is None:
            self.automation.select_chat(action.message.chat_name)
            time.sleep(2)
        self.automation.send_message(action.message.content)

    def _handle_react_action(self, action: ReactAction, friend: str | None) -> None:
        print(f"[red]Reacting with[/red] {action.emoji_name} [red]to[/red] {action.message_to_react.content}")
        print(action)
        if friend is None:
            self.automation.select_chat(action.message_to_react.chat_name)
            time.sleep(2)
        self.automation.react_to_message(emoji_query=action.emoji_name, text_contains=action.message_to_react.content, )

    def _handle_image_chat_action(self, action: ImageChatAction, friend: str | None) -> None:
        print(f"[red]Generating image:[/red] {action.prompt}")
        # generate into temp and send
        try:
            if action.model:
                paths = generate_image(
                    prompt=action.prompt,
                    n=max(1, action.n or 1),
                    model=action.model,
                    output_filename=(action.output_filename or "image_action"),
                )
            else:
                paths = generate_image(
                    prompt=action.prompt,
                    n=max(1, action.n or 1),
                    output_filename=(action.output_filename or "image_action"),
                )
        except Exception as e:
            print(f"[red]Failed to generate image:[/red] {e}")
            return
        if friend is None:
            self.automation.select_chat(action.chat_name)
            time.sleep(2)
        # Attach and send
        try:
            self.automation.attach_media([str(p) for p in paths])
        except Exception as e:
            print(f"[red]Failed to send generated image(s):[/red] {e}")

    def _handle_gif_chat_action(self, action: GifChatAction, friend: str | None) -> None:
        print(f"[red]Sending GIF for search:[/red] {action.search_term}")
        if friend is None:
            self.automation.select_chat(action.chat_name)
            time.sleep(2)
        try:
            ok = self.automation.send_gif_by_search(query=action.search_term, press_enter_to_send=action.press_enter_to_send)
            if not ok:
                print(f"[red]Failed to send GIF for search:[/red] {action.search_term}")
        except Exception as e:
            print(f"[red]Exception sending GIF:[/red] {e}")