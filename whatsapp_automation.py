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
from utils import parse_pre_plain_text, extract_message_text_from_elem

from dotenv import load_dotenv
load_dotenv()
os_name = os.environ.get("OPERATING_SYSTEM", "LINUX")

CONTROL_KEY = {
    "MAC": Keys.COMMAND,
    "LINUX": Keys.CONTROL,
}[os_name]

@dataclass
class WhatsAppMessage:
    """Represents a WhatsApp message."""
    sender: str
    content: str
    timestamp: datetime
    is_outgoing: bool
    chat_name: str


@dataclass
class ChatListEntry:
    """Represents a chat row in the sidebar list."""
    name: str
    preview: Optional[str]
    time_text: Optional[str]


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
        #service = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(options=chrome_options)
    
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
    
    def select_chat(self, contact_name: str) -> bool:
        """Select a chat by contact name."""
        
        # 1. Ensure the search input is visible & interactable
        def _activate_search():
            """Try clicking the sidebar search icon to reveal search box."""
            try:
                search_icon = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="chat-list-search"]')
                self.driver.execute_script("arguments[0].click();", search_icon)
                time.sleep(0.5)
                return 
            except Exception:
                pass
            # fallback: try generic search svg/icon
            try:
                icon_generic = self.driver.find_element(By.CSS_SELECTOR, 'span[data-icon="search"]')
                self.driver.execute_script("arguments[0].click();", icon_generic)
                time.sleep(0.5)
                return 
            except Exception:
                pass
            
            raise Exception("Failed to activate search.")
    
        try:
            search_box = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="3"]')
            if not (search_box.is_displayed() and search_box.is_enabled()):
                raise ElementNotInteractableException()
        except (NoSuchElementException, ElementNotInteractableException):
            _activate_search()
            search_box = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="3"]')

        try:
            # Interact with search box
            search_box.click()
            search_box.clear()
            search_box.send_keys(CONTROL_KEY + "a", Keys.DELETE)
            search_box.send_keys(contact_name)
            time.sleep(1)
            
            # Quick keyboard selection – press ENTER to open the first/highlighted result
            search_box.send_keys(Keys.RETURN)
            time.sleep(2)

            # Verify again
            if self._verify_chat_opened():
                logger.info(f"Successfully opened chat via keyboard: {contact_name}")
                return True
            
            return False

        except Exception as e:
            logger.error(f"Failed to select chat for '{contact_name}': {e}")
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
                    ActionChains(self.driver).key_down(CONTROL_KEY, target_elem).send_keys('a').key_up(CONTROL_KEY).perform()
                    ActionChains(self.driver).send_keys(Keys.DELETE).perform()
                    ActionChains(self.driver).key_down(CONTROL_KEY, target_elem).send_keys('v').key_up(CONTROL_KEY).perform()
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
    
    def _find_chat_list_container(self):
        """Find the sidebar chat list container using resilient selectors."""
        candidates = [
            'div[aria-label*="Chat list"]',
            'div[data-testid="chat-list"]',
            'div[role="grid"]',
        ]
        for sel in candidates:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                if elem and elem.is_displayed():
                    return elem
            except Exception:
                continue
        logger.error("Could not locate chat list container")
        return None

    def _ensure_search_box(self):
        """Ensure the sidebar search box is visible and return it."""
        # Try to locate; if not interactable, click search icon
        try:
            search_box = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="3"]')
            if search_box.is_displayed() and search_box.is_enabled():
                return search_box
        except Exception:
            pass

        # Activate search UI
        try:
            search_icon = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="chat-list-search"]')
            self.driver.execute_script("arguments[0].click();", search_icon)
            time.sleep(0.3)
        except Exception:
            try:
                icon_generic = self.driver.find_element(By.CSS_SELECTOR, 'span[data-icon="search"]')
                self.driver.execute_script("arguments[0].click();", icon_generic)
                time.sleep(0.3)
            except Exception:
                pass

        # Return (or raise) after activation
        return self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="3"]')

    def _clear_and_apply_search(self, text: Optional[str]) -> bool:
        """Clear the sidebar search, optionally apply a new search term."""
        try:
            sb = self._ensure_search_box()
            try:
                sb.click()
            except Exception:
                pass
            try:
                ActionChains(self.driver).key_down(CONTROL_KEY, sb).send_keys('a').key_up(CONTROL_KEY).perform()
                ActionChains(self.driver).send_keys(Keys.DELETE).perform()
            except Exception:
                try:
                    sb.clear()
                except Exception:
                    pass
            if text:
                sb.send_keys(text)
                time.sleep(0.6)
            else:
                time.sleep(0.2)

            # Scroll chat list to top after search change
            container = self._find_chat_list_container()
            if container:
                try:
                    self.driver.execute_script("arguments[0].scrollTop = 0;", container)
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.debug(f"Search clear/apply failed: {e}")
            return False

    def _scroll_chat_list_once(self, container) -> bool:
        """Scroll the chat list container by one viewport. Returns True if scrolled."""
        try:
            scroll_elem = container
            try:
                # Prefer inner grid if present
                inner = container.find_element(By.CSS_SELECTOR, 'div[role="grid"]')
                if inner and inner.is_displayed():
                    scroll_elem = inner
            except Exception:
                pass

            height = self.driver.execute_script("return arguments[0].clientHeight;", scroll_elem)
            before = self.driver.execute_script("return arguments[0].scrollTop;", scroll_elem)
            max_scroll = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_elem)
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].clientHeight;",
                scroll_elem,
            )
            time.sleep(0.25)
            after = self.driver.execute_script("return arguments[0].scrollTop;", scroll_elem)
            if after > before or (before + height) < max_scroll:
                return True
        except Exception:
            try:
                # Fallback: page down
                ActionChains(self.driver).send_keys(Keys.PAGE_DOWN).perform()
                time.sleep(0.2)
                return True
            except Exception:
                return False
        return False

    def get_visible_messages_simple(self, limit: int = 200) -> List[WhatsAppMessage]:
        """Simpler, robust collection of on-screen messages using message-in/out containers.

        - Select containers with classes containing 'message-in' or 'message-out'.
        - Read `data-pre-plain-text` from an element within each container to parse timestamp and sender.
        - Extract textual content from `span.selectable-text` descendants.
        """

        containers = self.driver.find_elements(By.CSS_SELECTOR, 'div.message-in, div.message-out')
        
        print(f"Found {len(containers)} containers, limiting to {limit}")
        containers = containers[-limit:]
        
        msgs: List[WhatsAppMessage] = []
        chat_name = self._get_current_chat_name()
        for c in containers:
            try:
                # Determine direction from class
                is_outgoing = 'message-out' in (c.get_attribute('class') or '').lower()

                # Parse meta
                pre_elem = c.find_element(By.CSS_SELECTOR, '[data-pre-plain-text]')

                ts, sender = parse_pre_plain_text(pre_elem.get_attribute('data-pre-plain-text') or '')
                
                if sender is None:
                    sender = 'You' if is_outgoing else chat_name

                # Content
                content = extract_message_text_from_elem(c)
                if not content:
                    print(f"No content found for {c}")
                    continue

                message = WhatsAppMessage(
                    sender=sender,
                    content=content,
                    timestamp=ts or datetime.now(),
                    is_outgoing=is_outgoing,
                    chat_name=chat_name,
                )
                msgs.append(message)
            except Exception as e:
                print(f"Error parsing message: {e}")
                continue
        return msgs

    def list_recent_chat_entries(self, max_rows: int = 30, max_scrolls: int = 40, search_term: Optional[str] = None) -> List[ChatListEntry]:
        """Return structured recent chat entries with name, preview, and time.

        - Name selector: within the chat grid cell col 2, `span[title]`.
        - Preview selector: within the same row, `span[dir="ltr"]:not([title])`.
        - Time selector: sibling `div._ak8i` (as seen in provided HTML), fallback to any time-like cell.
        """
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[aria-label*="Chat list"], div[data-testid="chat-list"], div[role="grid"]'))
            )
        except Exception:
            logger.error("Chat list did not appear in time")
            return []

        # Clear or apply the sidebar search before we collect
        self._clear_and_apply_search(search_term)

        container = self._find_chat_list_container()
        if not container:
            return []

        # Rows: commonly role=row; sometimes container children are row wrappers
        row_selectors = [
            'div[role="row"]',
            'div[aria-rowindex]',
            'div._ak8o'  # observed class on gridcell wrapper
        ]

        def get_rows():
            for rs in row_selectors:
                try:
                    rows = container.find_elements(By.CSS_SELECTOR, rs)
                    if rows:
                        return rows
                except Exception:
                    continue
            return []

        def parse_row(row) -> Optional[ChatListEntry]:
            try:
                # Prefer gridcell col 2 area to scope search
                scope = None
                try:
                    scope = row.find_element(By.CSS_SELECTOR, 'div[role="gridcell"][aria-colindex="2"], div._ak8o')
                except Exception:
                    scope = row

                name = None
                try:
                    name_el = scope.find_element(By.CSS_SELECTOR, 'span[dir="auto"][title], span[title]')
                    name = (name_el.get_attribute('title') or name_el.text or '').strip()
                except Exception:
                    pass

                if not name:
                    return None

                # Preview: span with dir ltr and without title attribute
                preview = None
                try:
                    preview_el = row.find_element(By.CSS_SELECTOR, 'span[dir="ltr"]:not([title])')
                    preview = (preview_el.text or '').strip()
                except Exception:
                    preview = None

                # Time: div with class _ak8i, or any element in time column
                time_text = None
                try:
                    time_el = row.find_element(By.CSS_SELECTOR, 'div._ak8i')
                    time_text = (time_el.text or '').strip()
                except Exception:
                    try:
                        time_el = row.find_element(By.CSS_SELECTOR, 'div[role="gridcell"][aria-colindex="3"]')
                        time_text = (time_el.text or '').strip()
                    except Exception:
                        time_text = None

                return ChatListEntry(name=name, preview=preview, time_text=time_text)
            except Exception:
                return None

        entries: List[ChatListEntry] = []
        seen_names: set[str] = set()
        no_growth_rounds = 0

        def collect():
            nonlocal entries
            new_added = 0
            for row in get_rows():
                ent = parse_row(row)
                if not ent:
                    continue
                if ent.name in seen_names:
                    continue
                seen_names.add(ent.name)
                entries.append(ent)
                new_added += 1
                if len(entries) >= max_rows:
                    break
            return new_added

        collect()
        if len(entries) >= max_rows:
            return entries[:max_rows]

        for _ in range(max_scrolls):
            progressed = self._scroll_chat_list_once(container)
            added = collect()
            if len(entries) >= max_rows:
                break
            if added == 0:
                no_growth_rounds += 1
            else:
                no_growth_rounds = 0
            if not progressed or no_growth_rounds >= 3:
                break

        return entries[:max_rows]

    def list_chat_names(self, max_rows: int = 30, max_scrolls: int = 40, search_term: Optional[str] = None):
        chat_entries = self.list_recent_chat_entries(max_rows, max_scrolls, search_term)
        chat_names = list([entry.name for entry in chat_entries])
        return chat_names
    
    async def stop(self):
        """Stop automation and cleanup."""
        logger.info("Stopping automation...")
        if self.driver:
            # Allow extra time for pending network/UI operations before closing
            await asyncio.sleep(5)
            self.driver.quit()
            self.driver = None
