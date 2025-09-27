# List all the chats in the WhatsApp Web app
# For each chat, load up to the last 1000 messages and save them to conversations/<chat>.json

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Tuple

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from whatsapp_automation import WhatsAppAutomation, WhatsAppMessage


def ensure_conversations_dir() -> str:
    base_dir = os.path.abspath("conversations")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def sanitize_filename(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", "."))
    safe = safe.strip().replace(" ", "_")
    if not safe:
        safe = "chat"
    return safe[:120]


def find_message_scroller(automation: WhatsAppAutomation):
    driver = automation.driver
    candidates = [
        'div[data-testid="conversation-panel-body"]',
        'div[aria-label*="Message list"]',
        'div[role="region"] div[tabindex="-1"]',
        'div[role="region"]',
    ]
    for sel in candidates:
        try:
            elems = driver.find_elements("css selector", sel)
            for e in elems:
                if e.is_displayed():
                    try:
                        h = driver.execute_script("return arguments[0].scrollHeight > arguments[0].clientHeight;", e)
                    except Exception:
                        h = True
                    if h:
                        return e
        except Exception:
            continue
    return None


def scroll_older_messages(automation: WhatsAppAutomation, max_passes: int = 60) -> None:
    driver = automation.driver
    scroller = find_message_scroller(automation)
    if not scroller:
        return

    # Focus scroller to make PageUp effective
    try:
        ActionChains(driver).move_to_element(scroller).click(scroller).perform()
    except Exception:
        pass

    # Incrementally page up to load older history
    for _ in range(max_passes):
        try:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop - arguments[0].clientHeight;", scroller)
        except Exception:
            # Fallback to keyboard PageUp
            try:
                ActionChains(driver).send_keys(Keys.PAGE_UP).perform()
            except Exception:
                break
        time.sleep(0.25)


def serialize_message(m: WhatsAppMessage) -> Dict:
    return {
        "sender": m.sender,
        "content": m.content,
        "is_outgoing": m.is_outgoing,
        "chat_name": m.chat_name,
        # Note: source DOM timestamp is not extracted; using scrape time per message
        "timestamp": m.timestamp.isoformat(),
    }


async def scrape_all_chats(limit_per_chat: int = 1000) -> None:
    conversations_dir = ensure_conversations_dir()
    automation = WhatsAppAutomation()
    try:
        await automation.start()

        chat_names = automation.list_chat_names(max_rows=500)
        if not chat_names:
            return

        for idx, chat in enumerate(chat_names, start=1):
            # Open chat
            if not automation.select_chat(chat):
                continue

            # Grow message window until we have enough or we stop making progress
            collected: Dict[Tuple[bool, str, str], WhatsAppMessage] = {}
            no_growth_rounds = 0
            while len(collected) < limit_per_chat and no_growth_rounds < 10:
                scroll_older_messages(automation, max_passes=12)
                msgs = automation.get_recent_messages(limit=limit_per_chat)
                before = len(collected)
                for m in msgs:
                    key = (m.is_outgoing, m.sender, m.content)
                    collected[key] = m
                after = len(collected)
                if after == before:
                    no_growth_rounds += 1
                else:
                    no_growth_rounds = 0

            # Persist to disk
            file_name = sanitize_filename(chat) + ".json"
            out_path = os.path.join(conversations_dir, file_name)
            ordered = list(collected.values())
            data = {
                "chat_name": chat,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "message_count": len(ordered),
                "messages": [serialize_message(m) for m in ordered[-limit_per_chat:]],
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    finally:
        await automation.stop()


if __name__ == "__main__":
    asyncio.run(scrape_all_chats(limit_per_chat=1000))
