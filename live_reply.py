#!/usr/bin/env python3
"""Run continuous live-reply for a chat."""
import asyncio
import typer
from typing import Optional
from utils import setup_logging, console
from whatsapp_automation import live_reply

def main(
    chat: str = typer.Argument(..., help="Chat name / number (or group)"),
    group: bool = typer.Option(False, "--group", "-g", help="Target a group chat"),
    sender: Optional[str] = typer.Option(None, "--sender", "-s", help="Filter by sender (optional)"),
    interval: int = typer.Option(5, "--interval", "-i", help="Poll interval seconds"),
):
    """Continuously reply to new messages in CHAT until Ctrl-C."""
    setup_logging()

    async def run():
        await live_reply(
            chat_name=chat,
            chat_type="group" if group else "individual",
            sender_alias=sender,
            poll_interval=interval,
        )

    console.print(f"🔄 Live-reply started for {chat}. Press Ctrl-C to stop.")
    asyncio.run(run())

if __name__ == "__main__":
    typer.run(main) 