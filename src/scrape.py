import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Iterable, List, Optional

from src.whatsapp_automation import WhatsAppAutomation
from src.schemas import WhatsAppMessage
import typer

class Scraper:
    def __init__(self):
        self.whatsapp_automation = WhatsAppAutomation()
        asyncio.run(self.whatsapp_automation.start())

    def _conversations_dir(self, base_dir: Optional[str] = None) -> str:
        if base_dir:
            out_dir = os.path.abspath(base_dir)
        else:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
            out_dir = os.path.join(project_root, "conversations")
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

    def _safe_filename(self, name: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
        return safe or "chat"

    def _serialize_messages(self, messages: Iterable[WhatsAppMessage]) -> List[dict]:
        def to_dict(m: WhatsAppMessage) -> dict:
            return {
                "sender": m.sender,
                "content": m.content,
                "timestamp": (m.timestamp.isoformat() if hasattr(m.timestamp, "isoformat") else str(m.timestamp)),
                "is_outgoing": m.is_outgoing,
                "chat_name": m.chat_name,
            }

        # Deduplicate by hash, then sort by timestamp asc
        unique = list({m: None for m in messages}.keys())
        try:
            unique.sort(key=lambda m: m.timestamp)
        except Exception:
            pass
        return [to_dict(m) for m in unique]

    def save_messages_json(self, chat_name: str, messages: Iterable[WhatsAppMessage], base_dir: Optional[str] = None) -> str:
        out_dir = self._conversations_dir(base_dir)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self._safe_filename(chat_name)}_{ts}.json"
        path = os.path.join(out_dir, filename)

        payload = {
            "chat_name": chat_name,
            "exported_at": datetime.now().isoformat(),
            "message_count": len(list(messages)) if not isinstance(messages, set) else len(messages),
            "messages": self._serialize_messages(messages),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def scrape_chat(self, chat_name: str, scrolls: int = 20, per_pass_limit: int = 200) -> List[WhatsAppMessage]:
        self.whatsapp_automation.select_chat(chat_name)
        time.sleep(0.5)
        messages: set[WhatsAppMessage] = set()

        for _ in range(scrolls):
            new_messages = self.whatsapp_automation.get_visible_messages_simple(per_pass_limit)
            for new_message in new_messages:
                if new_message not in messages:
                    messages.add(new_message)
            time.sleep(0.5)
            self.whatsapp_automation.scroll_chat()
            time.sleep(0.5)

        return list(messages)

    def shutdown(self):
        try:
            asyncio.run(self.whatsapp_automation.stop())
        except Exception:
            pass


app = typer.Typer(help="Scrape WhatsApp chats and save to JSON under conversations/.")


@app.command()
def chat(
    chat_name: str = typer.Argument(..., help="Exact chat name to open and scrape"),
    scrolls: int = typer.Option(20, help="How many scroll iterations to perform"),
    per_pass_limit: int = typer.Option(200, help="How many visible messages to examine per pass"),
    output_dir: Optional[str] = typer.Option(None, help="Custom output directory (defaults to project conversations/)")
):
    """Scrape a single chat and write a JSON file to conversations/."""
    scraper = Scraper()
    try:
        msgs = scraper.scrape_chat(chat_name, scrolls=scrolls, per_pass_limit=per_pass_limit)
        out_path = scraper.save_messages_json(chat_name, msgs, base_dir=output_dir)
        typer.echo(f"Saved {len(msgs)} messages to {out_path}")
    finally:
        scraper.shutdown()


@app.command()
def batch(
    chats: List[str] = typer.Argument(..., help="One or more chat names", metavar="CHAT..."),
    scrolls: int = typer.Option(20, help="How many scroll iterations per chat"),
    per_pass_limit: int = typer.Option(200, help="How many visible messages to examine per pass"),
    output_dir: Optional[str] = typer.Option(None, help="Custom output directory (defaults to project conversations/)")
):
    """Scrape multiple chats, each for N scrolls, saving one JSON per chat."""
    scraper = Scraper()
    try:
        for chat_name in chats:
            typer.echo(f"Scraping '{chat_name}' for {scrolls} scrolls…")
            msgs = scraper.scrape_chat(chat_name, scrolls=scrolls, per_pass_limit=per_pass_limit)
            out_path = scraper.save_messages_json(chat_name, msgs, base_dir=output_dir)
            typer.echo(f"  -> Saved {len(msgs)} messages to {out_path}")
    finally:
        scraper.shutdown()


if __name__ == "__main__":
    app()