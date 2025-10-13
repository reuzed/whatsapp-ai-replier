from src.whatsapp_automation import WhatsAppAutomation
from loguru import logger
import asyncio

# ------------------------------------------------------------
# Convenience: reply to N recent incoming messages for a contact
# ------------------------------------------------------------

async def reply_to_contact(
    chat_name: str,
    sender_alias: str | None = None,
    replies_limit: int | None = None,
    chat_type: str = "individual",
) -> int:
    """Reply to every incoming message from *sender_alias* **since your last
    message**.

    This opens the chat, finds the most recent outgoing message from *you*, then
    iterates over all later messages that match the given sender, replying to
    each one (up to *replies_limit* if provided).
    """
    automation = WhatsAppAutomation()
    sent = 0
    try:
        await automation.start()

        if not automation.select_chat(chat_name, chat_type=chat_type):
            logger.error("Could not open chat – aborting auto-reply")
            return 0

        # Fetch a generous window (WhatsApp loads lazy, so 50 is usually safe)
        messages = automation.get_recent_messages(limit=50)

        # Identify index of the latest outgoing message
        last_out_idx = None
        for idx in range(len(messages) - 1, -1, -1):
            if messages[idx].is_outgoing:
                last_out_idx = idx
                break

        # Slice to only the messages *after* our last one
        candidates = messages[last_out_idx + 1 :] if last_out_idx is not None else messages

        for msg in candidates:
            if msg.is_outgoing:
                continue  # Shouldn't happen but guard
            if sender_alias and msg.sender.lower() != sender_alias.lower():
                continue
            if replies_limit and sent >= replies_limit:
                break

            # Include last 30 messages before this msg as context
            try:
                idx = messages.index(msg)
            except ValueError:
                idx = 0
            prior = messages[max(0, idx - 30):idx]
            history = []
            for e in prior:
                if e.is_outgoing:
                    history.append({"role": "assistant", "content": e.content})
                else:
                    history.append({"role": "user", "content": f"{e.sender}: {e.content}"})

            response = await automation.llm_manager.generate_whatsapp_response(
                msg.content, msg.sender, history
            )

            if automation.send_message(response):
                sent += 1
                logger.info("Sent auto-reply %s/%s", sent, replies_limit or '∞')
                await asyncio.sleep(1)

        return sent
    finally:
        await automation.stop() 

# ------------------------------------------------------------
# Live reply coroutine
# ------------------------------------------------------------

async def live_reply(
    chat_name: str,
    chat_type: str = "individual",
    sender_alias: str | None = None,
    poll_interval: int = 5,
) -> None:
    """Continuously monitor *chat_name* and reply to new incoming messages.

    Stops on Ctrl-C.
    """
    automation = WhatsAppAutomation()
    processed: set[str] = set()
    try:
        await automation.start()

        if not automation.select_chat(chat_name):
            logger.error("Could not open chat – exiting live reply")
            return

        from datetime import datetime
        start_time = datetime.now()

        # mark existing messages as already seen
        for m in automation.get_recent_messages(50):
            processed.add(f"{m.sender}_{m.content}")

        logger.info("Live-reply started for %s", chat_name)

        while True:
            # get last 30 messages
            msgs = automation.get_recent_messages(30)
            for m in msgs:
                mid = f"{m.sender}_{m.content}"
                if m.timestamp <= start_time or mid in processed or m.is_outgoing:
                    continue
                if sender_alias and m.sender.lower() != sender_alias.lower():
                    continue

                # Build brief context: last 30 messages before current m
                try:
                    idx = msgs.index(m)
                except ValueError:
                    idx = 0
                prior = msgs[max(0, idx - 30):idx]
                history = []
                for e in prior:
                    if e.is_outgoing:
                        history.append({"role": "assistant", "content": e.content})
                    else:
                        history.append({"role": "user", "content": f"{e.sender}: {e.content}"})

                response = await automation.llm_manager.generate_whatsapp_response(
                    m.content, m.sender, history
                )
                if automation.send_message(response):
                    processed.add(mid)
                    logger.info("Replied to message at %s", m.timestamp.strftime("%H:%M:%S"))
                    await asyncio.sleep(1)

            await asyncio.sleep(poll_interval)

    except KeyboardInterrupt:
        logger.info("Live-reply stopped by user")
    finally:
        await automation.stop() 
