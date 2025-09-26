import os
from rich.console import Console
from loguru import logger
from config import settings

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