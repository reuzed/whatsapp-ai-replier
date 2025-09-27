import os
from rich.console import Console
from loguru import logger
from config import settings
import re
from datetime import datetime
from typing import Optional, Tuple

console = Console()

def setup_logging():
    """Configure loguru to file + rich console."""
    os.makedirs("logs", exist_ok=True)

    logger.remove()
    logger.add(
        settings.log_file,
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        rotation="1 MB",
        retention="7 days",
    )
    logger.add(
        lambda msg: console.print(msg, style="dim"),
        level=settings.log_level,
        format="{time:HH:mm:ss} | {level} | {message}",
    ) 


def parse_pre_plain_text(pre: str) -> Tuple[Optional[datetime], Optional[str]]:
    """Parse WhatsApp's data-pre-plain-text header.

    Example: "[23:26, 26/09/2025] Reu: " -> (datetime(...), "Reu")

    Returns (timestamp, sender). If parsing fails, returns (None, None).
    """
    if not pre:
        return None, None
    try:
        # Match [HH:MM, DD/MM/YYYY] Sender:
        m = re.match(r"\[(\d{1,2}:\d{2}),\s*(\d{1,2}/\d{1,2}/\d{2,4})\]\s*(.*?):\s*$", pre.strip())
        if not m:
            # Alternative variant: [DD/MM/YY, HH:MM] Sender:
            m = re.match(r"\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2})\]\s*(.*?):\s*$", pre.strip())
            if m:
                date_str, time_str, sender = m.groups()
                # Day-first
                for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%y %H:%M"):
                    try:
                        ts = datetime.strptime(f"{date_str} {time_str}", fmt)
                        return ts, sender
                    except Exception:
                        continue
                return None, sender
            return None, None
        time_str, date_str, sender = m.groups()
        # Day-first
        for fmt in ("%H:%M %d/%m/%Y", "%H:%M %d/%m/%y"):
            try:
                ts = datetime.strptime(f"{time_str} {date_str}", fmt)
                return ts, sender
            except Exception:
                continue
        return None, sender
    except Exception:
        return None, None


def extract_message_text_from_elem(elem) -> str:
    """Extract the visible text content for a message container element.

    Tries `span.selectable-text` children first; falls back to the container's text.
    """
    try:
        parts = []
        spans = elem.find_elements_by_css_selector('span.selectable-text, div.selectable-text') if hasattr(elem, 'find_elements_by_css_selector') else elem.find_elements("css selector", 'span.selectable-text, div.selectable-text')
        for s in spans:
            t = (s.text or '').strip()
            if t:
                parts.append(t)
        if parts:
            return "\n".join(parts)
    except Exception:
        pass
    try:
        return (elem.text or '').strip()
    except Exception:
        return ""