"""Simplified WhatsApp Web automation using Selenium."""
import time
import os
import asyncio
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException, NoSuchElementException
from loguru import logger
import html
import subprocess
from selenium.webdriver.common.action_chains import ActionChains

from config import settings
from llm_client import LLMManager

@dataclass
class WhatsAppMessage:
    """Represents a WhatsApp message."""
    sender: str
    content: str
    timestamp: datetime
    is_outgoing: bool
    chat_name: str


class WhatsAppAutomation:
    """Simplified WhatsApp Web automation."""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.llm_manager = LLMManager()
        self.processed_messages: set = set()
        
    def setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver."""
        chrome_options = Options()
        
        # Choose profile directory: use configured path if provided, otherwise default
        # to a local ./whatsapp_profile directory (auto-created if missing).
        profile_dir = settings.chrome_profile_path or os.path.abspath("whatsapp_profile")
        os.makedirs(profile_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={profile_dir}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        service = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=service, options=chrome_options)
    
    async def start(self):
        """Start the WhatsApp automation."""
        logger.info("Starting WhatsApp automation...")
        try:
            self.driver = self.setup_driver()
            await self.connect_to_whatsapp()
        except Exception as e:
            logger.error(f"Failed to start: {e}")
            await self.stop()
            raise
    
    async def connect_to_whatsapp(self):
        """Connect to WhatsApp Web."""
        logger.info("Connecting to WhatsApp Web...")
        self.driver.get("https://web.whatsapp.com")
        try:
            # Check if already logged in
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[aria-label*="Chat list"]'))
            )
            logger.info("Already logged in")
        except TimeoutException:
            logger.info("Please scan QR code...")
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[aria-label*="Chat list"]'))
            )
            logger.info("Successfully logged in")
    
    def select_chat(self, contact_name: str, chat_type: str = "individual") -> bool:
        """Select a chat by contact name."""
        try:
            # 1. Ensure the search input is visible & interactable
            def _activate_search():
                """Try clicking the sidebar search icon to reveal search box."""
                try:
                    search_icon = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="chat-list-search"]')
                    self.driver.execute_script("arguments[0].click();", search_icon)
                    time.sleep(0.5)
                except Exception:
                    # fallback: try generic search svg/icon
                    try:
                        icon_generic = self.driver.find_element(By.CSS_SELECTOR, 'span[data-icon="search"]')
                        self.driver.execute_script("arguments[0].click();", icon_generic)
                        time.sleep(0.5)
                    except Exception:
                        pass

            try:
                search_box = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="3"]')
                if not (search_box.is_displayed() and search_box.is_enabled()):
                    raise ElementNotInteractableException()
            except (NoSuchElementException, ElementNotInteractableException):
                _activate_search()
                search_box = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="3"]')

            # Interact with search box
            search_box.click()
            search_box.clear()
            search_box.send_keys(Keys.CONTROL + "a", Keys.DELETE)
            search_box.send_keys(contact_name)
            time.sleep(1)
            
            # Quick keyboard selection – press ENTER to open the first/highlighted result
            search_box.send_keys(Keys.RETURN)
            time.sleep(2)

            # Verify again
            if self._verify_chat_opened():
                logger.info(f"Successfully opened {chat_type} chat via keyboard: {contact_name}")
                return True
            
            return False

        except Exception as e:
            logger.error(f"Failed to select {chat_type} chat for '{contact_name}': {e}")
            return False
    
    def _verify_chat_opened(self) -> bool:
        """Verify a chat is open by reliably finding the message compose box."""
        try:
            # Wait up to 5 seconds for the compose box to appear
            wait = WebDriverWait(self.driver, 5)
            compose_box = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]'))
            )
            # Ensure it's visible and at the bottom of the screen
            if compose_box and compose_box.is_displayed() and compose_box.location['y'] > 400:
                return True
        except TimeoutException:
            logger.debug("Verification failed: Could not find message compose box.")
            return False
        return False
    
    def send_message(self, message: str) -> bool:
        """Send a message to current chat using the compose box and Enter key."""
        try:
            time.sleep(1)  # small pause for chat to stabilise

            input_selectors = [
                'div[data-testid="conversation-compose-box-input"]',
                'div[contenteditable="true"][data-tab="10"]',
            ]

            message_box = None
            for selector in input_selectors:
                try:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for e in elems:
                        if e.is_displayed() and e.is_enabled() and e.location["y"] > 200:
                            message_box = e
                            logger.info(f"Found message input using {selector}")
                            break
                    if message_box:
                        break
                except Exception:
                    continue

            if not message_box:
                logger.error("Could not locate message input box")
                return False

            # Focus and send the text followed by Enter
            message_box.click()
            try:
                message_box.clear()  # can fail for contenteditable on some Chrome versions
            except Exception:
                pass

            target_elem = message_box  # ensure we write into the observed compose box

            # Try fast human-like paste first (works best in non-headless)
            inserted = False
            try:
                try:
                    self.driver.execute_cdp_cmd('Browser.grantPermissions', {
                        'origin': 'https://web.whatsapp.com',
                        'permissions': ['clipboardReadWrite', 'clipboardSanitizedWrite'],
                    })
                except Exception:
                    pass

                # Write to clipboard via async script, then paste with Ctrl+V
                try:
                    res = self.driver.execute_async_script(
                        """
                        const txt = arguments[0];
                        const cb = arguments[arguments.length-1];
                        (async () => {
                          try { await navigator.clipboard.writeText(txt); cb(true); }
                          catch(e) { cb('ERR:' + (e && e.message ? e.message : 'unknown')); }
                        })();
                        """,
                        message,
                    )
                except Exception as e:
                    res = f"ERR:{e}"

                if res is True:
                    # Select-all then paste to replace any draft text
                    ActionChains(self.driver).key_down(Keys.CONTROL, target_elem).send_keys('a').key_up(Keys.CONTROL).perform()
                    ActionChains(self.driver).send_keys(Keys.DELETE).perform()
                    ActionChains(self.driver).key_down(Keys.CONTROL, target_elem).send_keys('v').key_up(Keys.CONTROL).perform()
                    try:
                        WebDriverWait(self.driver, 0.6).until(
                            lambda d: (target_elem.get_attribute('innerText') or '').strip() != ''
                        )
                        inserted = True
                    except Exception:
                        inserted = False
                else:
                    # Fallback: OS clipboard via xclip if available
                    try:
                        subprocess.run(['xclip', '-selection', 'clipboard'], input=message.encode('utf-8'), check=True)
                        ActionChains(self.driver).key_down(Keys.CONTROL, target_elem).send_keys('a').key_up(Keys.CONTROL).perform()
                        ActionChains(self.driver).send_keys(Keys.DELETE).perform()
                        ActionChains(self.driver).key_down(Keys.CONTROL, target_elem).send_keys('v').key_up(Keys.CONTROL).perform()
                        try:
                            WebDriverWait(self.driver, 0.6).until(
                                lambda d: (target_elem.get_attribute('innerText') or '').strip() != ''
                            )
                            inserted = True
                        except Exception:
                            inserted = False
                    except Exception:
                        inserted = False
            except Exception:
                inserted = False

            # If paste did not land, abort without attempting other insertion methods
            if not inserted:
                logger.error("Paste failed; aborting send to avoid slow fallbacks")
                return False
 
            # Content is present after paste (verified above), proceed to send

            # Send by clicking the send button (faster and more reliable than Enter)
            sent = False
            for sel in [
                'span[data-testid="send"]',
                'button[data-testid="compose-btn-send"]',
            ]:
                try:
                    send_btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if send_btn and send_btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", send_btn)
                        sent = True
                        break
                except Exception:
                    continue
            if not sent:
                target_elem.send_keys(Keys.RETURN)

            # Briefly wait for compose to clear instead of a fixed sleep
            try:
                WebDriverWait(self.driver, 1.5).until(lambda d: (target_elem.text or '').strip() == '')
            except Exception:
                pass

            logger.info(f"Message sent to {self._get_current_chat_name()}: {message[:50]}… (fast insert)")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def get_recent_messages(self, limit: int = 10) -> List[WhatsAppMessage]:
        """Get recent messages from current chat."""
        try:
            # Try multiple selectors for message containers
            message_selectors = [
                '[data-testid="msg-container"]',  # Original
                'span.selectable-text'  # Direct text spans
            ]
            
            message_elements = []
            working_selector = None
            
            for selector in message_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        message_elements = elements
                        working_selector = selector
                        logger.info(f"Found {len(elements)} message elements using {selector}")
                        break
                except Exception:
                    continue
            
            if not message_elements:
                logger.error("No message elements found with any selector")
                return []
            
            messages = []
            chat_name = self._get_current_chat_name()
            
            for elem in message_elements[-limit:]:
                try:
                    # Try to get text content
                    content = ""
                    text_selectors = ['span.selectable-text', 'span', 'div']
                    
                    for text_sel in text_selectors:
                        try:
                            content_elem = elem.find_element(By.CSS_SELECTOR, text_sel)
                            content = content_elem.text.strip()
                            if content:
                                break
                        except:
                            continue
                    
                    # If no content found, try getting text directly
                    if not content:
                        content = elem.text.strip()
                    
                    if not content:
                        continue
                    
                    # Determine if outgoing - try multiple ways
                    is_outgoing = False
                    try:
                        elem_class = elem.get_attribute("class") or ""
                        parent_class = elem.find_element(By.XPATH, './..').get_attribute("class") or ""
                        
                        if "message-out" in elem_class or "message-out" in parent_class:
                            is_outgoing = True
                        elif "message-in" in elem_class or "message-in" in parent_class:
                            is_outgoing = False
                        else:
                            # Position-based detection as fallback
                            location = elem.location
                            window_width = self.driver.get_window_size()['width']
                            is_outgoing = (location['x'] + elem.size['width']) > (window_width * 0.6)
                    except:
                        pass
                    
                    # Determine sender properly in group chats
                    sender = "You" if is_outgoing else chat_name
                    if not is_outgoing:
                        # Look for a span/div with data-pre-plain-text just before or inside elem
                        meta_elem = None
                        try:
                            meta_elem = elem.find_element(By.XPATH, './preceding-sibling::*[@data-pre-plain-text][1]')
                        except Exception:
                            try:
                                meta_elem = elem.find_element(By.XPATH, './/*[@data-pre-plain-text]')
                            except Exception:
                                meta_elem = None
                        if meta_elem:
                            pre_plain = meta_elem.get_attribute('data-pre-plain-text') or ''
                            if ']' in pre_plain and ':' in pre_plain:
                                try:
                                    sender_candidate = pre_plain.split(']')[1].split(':')[0].strip()
                                    if sender_candidate:
                                        sender = sender_candidate
                                except Exception:
                                    pass
                    
                    message = WhatsAppMessage(
                        sender=sender,
                        content=content,
                        timestamp=datetime.now(),
                        is_outgoing=is_outgoing,
                        chat_name=chat_name
                    )
                    
                    messages.append(message)
                    
                except Exception:
                    continue
            
            logger.info(f"Successfully retrieved {len(messages)} messages")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def _get_current_chat_name(self) -> str:
        """Get current chat name."""
        try:
            title_elem = self.driver.find_element(By.CSS_SELECTOR, 'header span[title]')
            return title_elem.get_attribute('title') or title_elem.text
        except:
            return "Unknown Chat"
    
    async def stop(self):
        """Stop automation and cleanup."""
        logger.info("Stopping automation...")
        if self.driver:
            # Allow extra time for pending network/UI operations before closing
            await asyncio.sleep(5)
            self.driver.quit()
            self.driver = None

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

        if not automation.select_chat(chat_name, chat_type=chat_type):
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

# ------------------------------------------------------------
# Auto sign-up live responder (string processing only)
# ------------------------------------------------------------

import re

def _parse_signup_list(text: str):
    """Return (total_bullets, names_list) if text looks like a numbered list else None."""
    raw_lines = [l.strip() for l in text.splitlines()]
    # find first bullet line
    start = 0
    pattern = re.compile(r"^\d+\)\s*")
    while start < len(raw_lines) and not pattern.match(raw_lines[start]):
        start += 1
    # Do not filter out empty lines; we want to preserve spacing in the tail
    lines = raw_lines[start:]
    pattern = re.compile(r"^(\d+)\)\s*(.*)$")
    bullets = []
    nums = []
    tail_text = ""
    for idx, ln in enumerate(lines):
        m = pattern.match(ln)
        if not m:
            # everything from here to end is extra commentary/footer (preserve verbatim spacing)
            tail_text = "\n".join(lines[idx:])
            break  # stop parsing bullets
        nums.append(int(m.group(1)))
        bullets.append(m.group(2).strip())  # may be empty
    # verify numbering sequential starting at 1
    if nums != list(range(1, len(nums) + 1)):
        return None
    return len(bullets), bullets, tail_text

async def auto_signup_live(
    chat_name: str,
    poll_interval: int = 10,
    my_name: str = "Matthew",
):
    """Continuously watch group sign-up list and add *my_name* when criteria met."""

    automation = WhatsAppAutomation()
    processed: set[str] = set()

    from datetime import datetime

    try:
        await automation.start()
        if not automation.select_chat(chat_name, chat_type="group"):
            logger.error("Cannot open group chat %s", chat_name)
            return

        # Mark all current messages as processed so we only handle NEW messages
        for m in automation.get_recent_messages(50):
            processed.add(m.content)

        start_time = datetime.now()

        while True:
            msgs = automation.get_recent_messages(5)
            # look at newest incoming message after script started
            incoming = [m for m in msgs if (not m.is_outgoing) and (m.timestamp > start_time)]
            if not incoming:
                await asyncio.sleep(poll_interval)
                continue
            latest = incoming[-1]
            key = latest.content
            if key in processed:
                await asyncio.sleep(poll_interval)
                continue
            parsed = _parse_signup_list(latest.content)
            if not parsed:
                print("Not parsed correctly")
                print(key)
                processed.add(key)  # not a list – mark so we don't re-parse
                await asyncio.sleep(poll_interval)
                continue
            total_bullets, names, tail_text = parsed
            filled = [n for n in names if n]
            # require at least 3 names already and ensure we're not already on it
            if my_name in names: # len(filled) < 3 or, could sign up after first
                processed.add(key)
                await asyncio.sleep(poll_interval)
                continue
            # insert ourselves at first empty slot (or append)
            added_name = False
            for idx, name in enumerate(names):
                if not name:
                    names[idx] = my_name
                    added_name = True
                    break
            if added_name:
                # Preserve original header (lines before first bullet)
                raw_lines = latest.content.splitlines()
                bullet_start = 0
                bullet_pat = re.compile(r"^\d+\)")
                while bullet_start < len(raw_lines) and not bullet_pat.match(raw_lines[bullet_start].strip()):
                    bullet_start += 1
                header_lines = raw_lines[:bullet_start]

                lines_out = [f"{i+1}) {names[i] if i < len(names) else ''}" for i in range(total_bullets)]
                reply_text = "\n".join(header_lines + lines_out)
                if tail_text:
                    if not reply_text.endswith("\n"):
                        reply_text += "\n"
                    reply_text += tail_text
                if automation.send_message(reply_text):
                    # Give WhatsApp time to send before tearing down the session
                    await asyncio.sleep(2)
                    logger.info("Auto-signed up. Added '%s' at position %d", my_name, names.index(my_name) + 1)
                    processed.add(key)
                    break  # message sent – exit loop
            await asyncio.sleep(poll_interval)

    except KeyboardInterrupt:
        logger.info("Auto-signup stopped")
    finally:
        await automation.stop()