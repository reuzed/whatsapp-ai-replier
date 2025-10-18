import asyncio
import sys
import argparse
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.theme import Theme

from src.whatsapp_automation import WhatsAppAutomation


custom_theme = Theme({
    "info": "cyan",
    "ok": "green",
    "warn": "yellow",
    "error": "bold red",
    "title": "bold magenta",
})
console = Console(theme=custom_theme)


class AutomationShell:
    def __init__(self) -> None:
        self.automation = WhatsAppAutomation()
        self.started = False

    async def start(self) -> None:
        if self.started:
            console.print("[warn]Already started[/warn]")
            return
        console.print(Panel.fit("Launching browser and connecting to WhatsApp Web...", title="[title]Start[/title]"))
        try:
            await self.automation.start()
            self.started = True
            console.print("[ok]Connected. If required, scan the QR code in the opened window.[/ok]")
        except Exception as e:
            console.print(f"[error]Failed to start: {e}[/error]")

    async def stop(self) -> None:
        if not self.started:
            console.print("[warn]Not running[/warn]")
            return
        console.print(Panel.fit("Stopping and closing browser...", title="[title]Stop[/title]"))
        try:
            await self.automation.stop()
            self.started = False
            console.print("[ok]Stopped[/ok]")
        except Exception as e:
            console.print(f"[error]Failed to stop: {e}[/error]")

    def _ensure_started(self) -> bool:
        if not self.started:
            console.print("[warn]Start the automation first (command: start)[/warn]")
            return False
        return True

    def select_chat(self, term: str) -> None:
        if not self._ensure_started():
            return
        info = self.automation.select_chat(term)
        if info:
            console.print(f"[ok]Opened chat[/ok]: [bold]{info.chat_name}[/bold] (group={info.is_group}) :: {info.extra_info}")
        else:
            console.print("[warn]No chat opened[/warn]")

    def who(self) -> None:
        if not self._ensure_started():
            return
        info = self.automation.which_chat_is_open()
        if info:
            console.print(f"[ok]Current chat[/ok]: [bold]{info.chat_name}[/bold] (group={info.is_group}) :: {info.extra_info}")
        else:
            console.print("[warn]No chat open[/warn]")

    def send(self, text_to_send: str) -> None:
        if not self._ensure_started():
            return
        ok = self.automation.send_message(text_to_send)
        if ok:
            console.print("[ok]Message sent[/ok]")
        else:
            console.print("[warn]Failed to send[/warn]")

    def list_chats(self, search: Optional[str] = None, max_rows: int = 30) -> None:
        if not self._ensure_started():
            return
        names = self.automation.list_chat_names(max_rows=max_rows, max_scrolls=40, search_term=search)
        table = Table(title="Recent Chats", show_lines=True)
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Name", style="white")
        for idx, name in enumerate(names, start=1):
            table.add_row(str(idx), name)
        console.print(table)

    def list_messages(self, limit: int = 30, simple: bool = True) -> None:
        if not self._ensure_started():
            return
        if simple:
            msgs = self.automation.get_visible_messages_simple(limit)
        else:
            msgs = self.automation.get_recent_messages(limit)

        table = Table(title="Visible Messages", show_lines=False)
        table.add_column("When", style="cyan")
        table.add_column("Sender", style="magenta")
        table.add_column("Text", style="white")
        for m in msgs:
            when = m.timestamp.strftime("%H:%M:%S") if hasattr(m, "timestamp") and m.timestamp else "?"
            sender_style = "green" if getattr(m, "is_outgoing", False) else "magenta"
            sender = Text(m.sender, style=sender_style)
            content = Text(m.content)
            table.add_row(when, sender, content)
        console.print(table)

    def scroll(self, direction: str) -> None:
        if not self._ensure_started():
            return
        ok = self.automation.scroll_chat(direction=direction)
        if ok:
            console.print(f"[ok]Scrolled {direction}[/ok]")
        else:
            console.print("[warn]Did not scroll[/warn]")

    def react_latest_in(self, emoji_query: str) -> None:
        if not self._ensure_started():
            return
        ok = self.automation.react_to_latest_incoming(emoji_query)
        console.print("[ok]Reaction applied[/ok]" if ok else "[warn]Failed to react[/warn]")

    def react_latest_out(self, emoji_query: str) -> None:
        if not self._ensure_started():
            return
        ok = self.automation.react_to_latest_outgoing(emoji_query)
        console.print("[ok]Reaction applied[/ok]" if ok else "[warn]Failed to react[/warn]")

    def react_contains(self, text_sub: str, emoji_query: str, incoming: Optional[bool]) -> None:
        if not self._ensure_started():
            return
        ok = self.automation.react_to_message_containing(text_sub, emoji_query, incoming=incoming)
        console.print("[ok]Reaction applied[/ok]" if ok else "[warn]Failed to react[/warn]")

    def help(self) -> None:
        table = Table(title="Commands", show_lines=True)
        table.add_column("Command", style="cyan")
        table.add_column("Usage", style="white")
        table.add_column("Description", style="green")
        rows = [
            ("start", "start", "Start the automation and open WhatsApp Web"),
            ("stop", "stop", "Stop and close the browser"),
            ("who", "who", "Show which chat is open"),
            ("select", "select <search>", "Open chat by search term"),
            ("send", "send <text>", "Send a message to current chat"),
            ("chats", "chats [search]", "List recent chats; optional filter"),
            ("msgs", "msgs [limit]", "List visible messages (simple parser)"),
            ("msgs_full", "msgs_full [limit]", "List recent messages (legacy parser)"),
            ("scroll", "scroll <up|down>", "Scroll conversation view"),
            ("react_in", "react_in <emoji>", "React to latest incoming message"),
            ("react_out", "react_out <emoji>", "React to latest outgoing message"),
            ("react_contains", "react_contains <text> <emoji> [incoming|outgoing|either]", "React to message containing text"),
            ("gif", "gif <search>", "Search Tenor and send first GIF"),
            ("attach", "attach <file> [more files...]", "Attach and send media files"),
            ("reply", "reply <text> [incoming|outgoing|either] [index]", "Reply to a specific message"),
            ("reply_contains", "reply_contains <substring> :: <reply> [incoming|outgoing|either]", "Reply to a message containing substring"),
            ("typing", "typing [seconds]", "Simulate typing indicator"),
            ("help", "help", "Show this help"),
            ("quit", "quit", "Exit"),
        ]
        for cmd, usage, desc in rows:
            table.add_row(cmd, usage, desc)
        console.print(table)


async def repl(preselect_chat: Optional[str] = None) -> None:
    console.print(Panel.fit("WhatsApp Automation Test Shell", title="[title]WhatsApp AI Replier[/title]"))
    shell = AutomationShell()
    # Optional auto-start and chat selection
    if preselect_chat:
        try:
            await shell.start()
            shell.select_chat(preselect_chat)
        except Exception as e:
            console.print(f"[warn]Auto-start/select failed: {e}[/warn]")
    shell.help()

    while True:
        try:
            line = Prompt.ask("[info]wa>[/info]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[warn]Exiting...[/warn]")
            break

        if not line:
            continue
        parts = line.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd in ("quit", "exit", "q"):
                if shell.started:
                    await shell.stop()
                break
            elif cmd == "help":
                shell.help()
            elif cmd == "start":
                await shell.start()
            elif cmd == "stop":
                await shell.stop()
            elif cmd == "who":
                shell.who()
            elif cmd == "select":
                if not args:
                    console.print("[warn]Usage: select <search-term>[/warn]")
                else:
                    shell.select_chat(" ".join(args))
            elif cmd == "send":
                if not args:
                    console.print("[warn]Usage: send <text>[/warn]")
                else:
                    shell.send(" ".join(args))
            elif cmd == "chats":
                search = None if not args else " ".join(args)
                shell.list_chats(search)
            elif cmd == "msgs":
                lim = int(args[0]) if args else 30
                shell.list_messages(limit=lim, simple=True)
            elif cmd == "msgs_full":
                lim = int(args[0]) if args else 30
                shell.list_messages(limit=lim, simple=False)
            elif cmd == "scroll":
                if not args or args[0] not in ("up", "down"):
                    console.print("[warn]Usage: scroll <up|down>[/warn]")
                else:
                    shell.scroll(args[0])
            elif cmd == "react_in":
                if not args:
                    console.print("[warn]Usage: react_in <emoji-query>[/warn]")
                else:
                    shell.react_latest_in(" ".join(args))
            elif cmd == "react_out":
                if not args:
                    console.print("[warn]Usage: react_out <emoji-query>[/warn]")
                else:
                    shell.react_latest_out(" ".join(args))
            elif cmd == "react_contains":
                if len(args) < 2:
                    console.print("[warn]Usage: react_contains <text> <emoji> [incoming|outgoing|either][/warn]")
                else:
                    incoming: Optional[bool]
                    incoming = None
                    if len(args) >= 3:
                        scope = args[-1].lower()
                        if scope in ("incoming", "in"):
                            incoming = True
                            text = " ".join(args[:-1])
                        elif scope in ("outgoing", "out"):
                            incoming = False
                            text = " ".join(args[:-1])
                        elif scope in ("either", "any"):
                            incoming = None
                            text = " ".join(args[:-1])
                        else:
                            text = " ".join(args[:-1])
                    else:
                        text = args[0]
                    emoji_query = args[1]
                    shell.react_contains(text, emoji_query, incoming)
            elif cmd == "gif":
                if not args:
                    console.print("[warn]Usage: gif <search>[/warn]")
                else:
                    ok = shell.automation.send_gif_by_search(" ".join(args))
                    console.print("[ok]GIF sent[/ok]" if ok else "[warn]Failed to send GIF[/warn]")
            elif cmd == "attach":
                if not args:
                    console.print("[warn]Usage: attach <file> [more files...] [/warn]")
                else:
                    ok = shell.automation.attach_media(args)
                    console.print("[ok]Media sent[/ok]" if ok else "[warn]Failed to send media[/warn]")
            elif cmd == "reply":
                if not args:
                    console.print("[warn]Usage: reply <text> [incoming|outgoing|either] [index][/warn]")
                else:
                    incoming_val = None
                    index_val = 1
                    # Parse optional flags from the end
                    if args and args[-1].isdigit():
                        index_val = int(args[-1])
                        args = args[:-1]
                    if args:
                        scope = args[-1].lower()
                        if scope in ("incoming", "in"):
                            incoming_val = True
                            args = args[:-1]
                        elif scope in ("outgoing", "out"):
                            incoming_val = False
                            args = args[:-1]
                        elif scope in ("either", "any"):
                            incoming_val = None
                            args = args[:-1]
                    reply_text = " ".join(args)
                    ok = shell.automation.reply_to_message(reply_text, index_from_end=index_val, incoming=incoming_val)
                    console.print("[ok]Replied[/ok]" if ok else "[warn]Failed to reply[/warn]")
            elif cmd == "reply_contains":
                if not args or "::" not in " ".join(args):
                    console.print("[warn]Usage: reply_contains <substring> :: <reply> [incoming|outgoing|either][/warn]")
                else:
                    joined = " ".join(args)
                    parts2 = [p.strip() for p in joined.split("::", 1)]
                    substr = parts2[0]
                    tail = parts2[1]
                    incoming_val = None
                    reply_text = tail
                    # Optional scope at end
                    tail_parts = tail.split()
                    if tail_parts:
                        scope = tail_parts[-1].lower()
                        if scope in ("incoming", "in"):
                            incoming_val = True
                            reply_text = " ".join(tail_parts[:-1])
                        elif scope in ("outgoing", "out"):
                            incoming_val = False
                            reply_text = " ".join(tail_parts[:-1])
                        elif scope in ("either", "any"):
                            incoming_val = None
                            reply_text = " ".join(tail_parts[:-1])
                    ok = shell.automation.reply_to_message_containing(substr, reply_text, incoming=incoming_val)
                    console.print("[ok]Replied[/ok]" if ok else "[warn]Failed to reply[/warn]")
            elif cmd == "typing":
                dur = float(args[0]) if args else 2.0
                ok = shell.automation.simulate_typing_indicator(duration_sec=dur)
                console.print("[ok]Typing simulated[/ok]" if ok else "[warn]Failed to simulate typing[/warn]")
            else:
                console.print("[warn]Unknown command. Type 'help' for commands.[/warn]")
        except Exception as e:
            console.print(f"[error]{e}[/error]")


def main() -> None:
    parser = argparse.ArgumentParser(description="WhatsApp Automation Test Shell")
    parser.add_argument("-chat", "--chat", dest="chat", help="Auto-start and open the specified chat name", default=None)
    args = parser.parse_args()
    try:
        asyncio.run(repl(preselect_chat=args.chat))
    except KeyboardInterrupt:
        console.print("\n[warn]Interrupted[/warn]")


if __name__ == "__main__":
    main()


