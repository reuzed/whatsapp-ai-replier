import asyncio
from whatsapp_automation import WhatsAppAutomation
from logging import getLogger
logger = getLogger("")

async def test() -> None:
    """Continuously monitor *chat_name* and reply to new incoming messages.

    Stops on Ctrl-C.
    """
    
    chat_name = "Matthew"
    chat_type: str = "individual",
    sender_alias: str | None = None,
    poll_interval: int = 5,
    
    automation = WhatsAppAutomation()
    
    await automation.start()

    processed: set[str] = set()
    
    print(automation.select_chat(chat_name, chat_type=chat_type))

    # from datetime import datetime
    # start_time = datetime.now()

    # # mark existing messages as already seen
    # for m in automation.get_recent_messages(50):
    #     processed.add(f"{m.sender}_{m.content}")

    # logger.info("Live-reply started for %s", chat_name)

    # while True:
    #     # get last 30 messages
    #     msgs = automation.get_recent_messages(30)
    #     for m in msgs:
    #         mid = f"{m.sender}_{m.content}"
    #         if m.timestamp <= start_time or mid in processed or m.is_outgoing:
    #             continue
    #         if sender_alias and m.sender.lower() != sender_alias.lower():
    #             continue

    #         # Build brief context: last 30 messages before current m
    #         try:
    #             idx = msgs.index(m)
    #         except ValueError:
    #             idx = 0
    #         prior = msgs[max(0, idx - 30):idx]
    #         history = []
    #         for e in prior:
    #             if e.is_outgoing:
    #                 history.append({"role": "assistant", "content": e.content})
    #             else:
    #                 history.append({"role": "user", "content": f"{e.sender}: {e.content}"})

    #         response = await automation.llm_manager.generate_whatsapp_response(
    #             m.content, m.sender, history
    #         )
    #         if automation.send_message(response):
    #             processed.add(mid)
    #             logger.info("Replied to message at %s", m.timestamp.strftime("%H:%M:%S"))
    #             await asyncio.sleep(1)

    #     await asyncio.sleep(poll_interval)

asyncio.run(test())