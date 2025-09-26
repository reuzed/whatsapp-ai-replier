#!/usr/bin/env python3
"""Reply to all unanswered messages in a chat (Typer CLI)."""
import asyncio
import typer
from typing import Optional

from utils import setup_logging, console
from whatsapp_automation import reply_to_contact

def main(
    chat: str = typer.Argument(..., help="Chat name / number (or group)"),
    sender: Optional[str] = typer.Option(None, "--sender", "-s", help="Filter by sender alias (optional)"),
    group: bool = typer.Option(False, "--group", "-g", help="Target a group chat"),
    limit: int = typer.Option(0, "--limit", "-l", help="Max replies (0 = all)"),
):
    """Reply to unanswered messages in CHAT."""

    setup_logging()

    async def run():
        sent = await reply_to_contact(
            chat_name=chat,
            sender_alias=sender,
            replies_limit=(limit or None),
            chat_type="group" if group else "individual",
        )
        console.print(f"✅ Replied to {sent} message(s)")

    asyncio.run(run())

if __name__ == "__main__":
    typer.run(main)