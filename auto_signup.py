#!/usr/bin/env python3
"""Automatic sign-up responder for group lists."""
import asyncio
import typer
from utils import setup_logging, console
from whatsapp_automation import auto_signup_live
from config import settings

def main(
    chat: str = typer.Argument(..., help="Group chat name"),
    interval: int = typer.Option(10, "--interval", "-i"),
    my_name: str = typer.Option(None, "--my-name", help="Override signup display name (defaults to env)"),
):
    setup_logging()
    async def run():
        name = my_name or settings.signup_my_name
        await auto_signup_live(chat_name=chat, poll_interval=interval, my_name=name)
    console.print(f"✍️  Auto-signup running in {chat}. Ctrl-C to stop.")
    asyncio.run(run())

if __name__ == "__main__":
    typer.run(main) 