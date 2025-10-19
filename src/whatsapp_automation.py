"""Simplified WhatsApp Web automation using Selenium."""
import time
import os
import asyncio
from typing import List, Optional, Tuple, Any
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException, NoSuchElementException
from loguru import logger
import html
import subprocess
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from pydantic import BaseModel
import pyperclip

from src.schemas import WhatsAppMessage, ChatListEntry

from src.config import settings
from src.utils import parse_pre_plain_text, extract_message_text_from_elem

from dotenv import load_dotenv
load_dotenv()
os_name = os.environ.get("OPERATING_SYSTEM", "LINUX")

CONTROL_KEY = {
    "MAC": Keys.COMMAND,
    "LINUX": Keys.CONTROL,
}[os_name]

class ChatInfo(BaseModel):
    chat_name: str
    is_group: bool
    extra_info: str

class WhatsAppAutomation:
    """Simplified WhatsApp Web automation."""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
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
        operating_system = os.environ.get("OPERATING_SYSTEM", "LINUX")
        if operating_system == "LINUX":
            return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=chrome_options)
        return webdriver.Chrome(options=chrome_options)
       
    async def connect_to_whatsapp(self):
        """Connect to WhatsApp Web."""
        if not self.driver:
            raise Exception("Driver not initialized")
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

    # ---------- Generic helpers ----------
    def _click_element(self, elem: WebElement) -> None:
        """Robustly click an element using JS fallback.

        - Scrolls into view
        - Tries JS click(), then native click()
        - No silent swallowing: raises if both strategies fail
        """
        if not self.driver:
            raise Exception("Driver not initialized")
        if elem is None:
            raise NoSuchElementException("Element is None")
        last_err: Optional[Exception] = None
        try:
            logger.debug("click_element: scrollIntoView")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", elem)
        except Exception as e:
            logger.debug(f"click_element: scrollIntoView failed: {e}")
        try:
            logger.debug("click_element: JS click")
            self.driver.execute_script("arguments[0].click();", elem)
            return
        except Exception as e:
            logger.debug(f"click_element: JS click failed: {e}")
            last_err = e
        try:
            logger.debug("click_element: native click")
            elem.click()
            return
        except Exception as e:
            logger.debug(f"click_element: native click failed: {e}")
            last_err = e
        raise last_err if last_err else Exception("Unknown click failure")

    def _find_first_displayed(self, selectors: List[str], scope: Optional[WebElement] = None) -> Optional[WebElement]:
        """Return the first displayed element found by any selector in order.

        scope: search inside this element if provided; otherwise search the driver.
        """
        if not self.driver:
            raise Exception("Driver not initialized")
        search_root: Any = scope or self.driver
        for css in selectors:
            try:
                elems = search_root.find_elements(By.CSS_SELECTOR, css)
                for e in elems:
                    if e and e.is_displayed():
                        return e
            except Exception:
                continue
        return None

    def _wait_for_any(self, selectors: List[str], timeout: float = 6.0, scope: Optional[WebElement] = None) -> Optional[WebElement]:
        """Wait up to timeout for first displayed element matching any selector."""
        end = time.time() + timeout
        while time.time() < end:
            el = self._find_first_displayed(selectors, scope=scope)
            if el:
                return el
            time.sleep(0.1)
        return None

    def _focus_element(self, elem: WebElement) -> None:
        """Scroll into view and focus an element, verifying activeElement when possible."""
        if not self.driver:
            raise Exception("Driver not initialized")
        try:
            logger.debug("focus_element: scrollIntoView")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        except Exception as e:
            logger.debug(f"focus_element: scrollIntoView failed: {e}")
        try:
            logger.debug("focus_element: click to focus")
            elem.click()
        except Exception as e:
            logger.debug(f"focus_element: click failed: {e}")
        try:
            logger.debug("focus_element: JS focus")
            self.driver.execute_script("arguments[0].focus();", elem)
        except Exception as e:
            logger.debug(f"focus_element: JS focus failed: {e}")
        try:
            focused = self.driver.execute_script("return document.activeElement === arguments[0];", elem)
            if not focused:
                logger.debug("focus_element: activeElement mismatch; retrying JS focus")
                self.driver.execute_script("arguments[0].focus();", elem)
        except Exception as e:
            logger.debug(f"focus_element: activeElement check failed: {e}")
    
    def focus_chat_list_search(self) -> Optional[WebElement]:
        """Focus the chat list search."""
        """The chat list search always has the following aria-label"""
        """aria-label="Search input textbox"""
        if not self.driver:
            raise Exception("Driver not initialized")
        
        try:
            search_box = self.driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Search input textbox"]')
        except Exception:
            return None
        
        time.sleep(0.5)
        
        if not (search_box.is_displayed() and search_box.is_enabled()):
            logger.error("Failed to focus chat list search.")
            return None
        
        search_box.click()
        time.sleep(0.5)
        return search_box
    
    def focus_message_box(self) -> Optional[WebElement]:
        """Focus the message box."""
        """The message box always has an aria-label of the form "Type to group <chat name>" or "Type to +44 78..."""
        """<div aria-label="Type to group T-Climbing Climbs/Sessions" </div>"""
        if not self.driver:
            raise Exception("Driver not initialized")
        
        try:
            message_box = self.driver.find_element(By.CSS_SELECTOR, 'div[aria-label^="Type to"]')
        except Exception:
            logger.error("Failed to focus message box.")
            return None
        
        message_box.click()
        time.sleep(0.1)
        return message_box
            
    def select_chat(self, search_term: str) -> Optional[ChatInfo]:
        '''Select a chat by contact name.'''
        search_box = self.focus_chat_list_search()
        if not search_box:
            raise Exception("Failed to activate search.")
    
        search_box.click()
        search_box.clear()
        search_box.send_keys(CONTROL_KEY + "a", Keys.DELETE)
        search_box.send_keys(search_term)
        time.sleep(1)
        
        # Quick keyboard selection – press ENTER to open the first/highlighted result
        search_box.send_keys(Keys.RETURN)
        time.sleep(2)

        # Verify again
        chat_info = self.which_chat_is_open()
        if chat_info:
            logger.info(f"Successfully opened chat {chat_info.chat_name} via search for: {search_term}")
            return chat_info
        
        return None
    
    def which_chat_is_open(self) -> Optional[ChatInfo]:
        """Get the name of the currently open chat."""
        """The message box always has an aria-label of the form "Type to group <chat name>" or "Type to +44 78..."""
        """For a person with a phone number, the title of the page is their contact name"""
        """<div aria-label="Type to group T-Climbing Climbs/Sessions" </div>"""
        if not self.driver:
            raise Exception("Driver not initialized")
        
        # Find aria label starting "Type to"... and extract the chat name
        try:
            aria_label = self.driver.find_element(By.CSS_SELECTOR, 'div[aria-label^="Type to"]').get_attribute('aria-label')
            if aria_label is None:
                logger.error("Did not find an open chat.")
                return None
        except:
            logger.info("Did not find an open chat.")
            return None
        
        if 'Type to group ' in aria_label:
            is_group = True
            chat_name = aria_label.split('Type to group ')[1]
        else:
            is_group = False
            chat_name = aria_label.split('Type to ')[1]
        
        try:
            title_elem = self.driver.find_element(By.CSS_SELECTOR, 'header span[title]')
            extra_info = title_elem.get_attribute('title') or title_elem.text
        except:
            # logger.error("Failed to get extra info from title element.")
            extra_info = "?"
        
        return ChatInfo(chat_name=chat_name, is_group=is_group, extra_info=extra_info)
        
    
    def send_message(self, message: str) -> bool:
        """Send a message to current chat using the compose box and Enter key."""

        message_box = self.focus_message_box()

        if not message_box:
            logger.error("Could not locate message input box to send message.")
            return False

        message_box.clear()  # can fail for contenteditable on some Chrome versions
        time.sleep(0.1)
        try:
            message_box.clear()
            # Fallback send with copy and paste
            pyperclip.copy(message)
            message_box.send_keys(CONTROL_KEY, 'v')
        except Exception:
            message_box.send_keys(message)
        message_box.send_keys(Keys.RETURN)
        time.sleep(0.5)
        return True

    def get_recent_messages(self, limit: int = 10) -> List[WhatsAppMessage]:
        """Get recent messages from current chat."""
        # This is to be deprecated in favour of the more general get_visible_messages_simple
        if not self.driver:
            raise Exception("Driver not initialized")
        
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
        if not self.driver:
            raise Exception("Driver not initialized")

        # Prefer deriving the chat name from the compose area's aria-label, which
        # encodes the real chat title (and not presence text like "online" or
        # "last seen ...").
        try:
            info = self.which_chat_is_open()
            if info and info.chat_name:
                return info.chat_name
        except Exception:
            pass

        # Fallback: old header lookup (may sometimes return presence text).
        try:
            title_elem = self.driver.find_element(By.CSS_SELECTOR, 'header span[title]')
            return title_elem.get_attribute('title') or title_elem.text
        except Exception:
            return "Unknown Chat"
    
    def _find_chat_list_container(self):
        """Find the sidebar chat list container using resilient selectors."""
        if not self.driver:
            raise Exception("Driver not initialized")
        
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
        if not self.driver:
            raise Exception("Driver not initialized")
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
        if not self.driver:
            raise Exception("Driver not initialized")
        
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
        if not self.driver:
            raise Exception("Driver not initialized")
        
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
                "window.scrollBy(0, -1000);",
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

    def scroll_chat_list(self) -> bool:
        """Scroll the chat list container by one viewport. Returns True if scrolled."""
        container = self._find_chat_list_container()
        if not container:
            return False
        
        return self._scroll_chat_list_once(container)

    def _find_message_list_container(self):
        """Find the message list (conversation) scroll container."""
        if not self.driver:
            raise Exception("Driver not initialized")
        
        candidates = [
            'div[aria-label*="Message list"]',
            'div[data-testid="conversation-panel-body"]',
            'div[data-testid="conversation-panel-wrapper"]',
        ]
        for sel in candidates:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                if elem and elem.is_displayed():
                    return elem
            except Exception:
                continue
        # Fallback: try to use a parent of any message bubble as the scroll container
        try:
            any_msg = self.driver.find_element(By.CSS_SELECTOR, 'div.message-in, div.message-out')
            parent = any_msg
            for _ in range(5):
                parent = parent.find_element(By.XPATH, './..')
                if parent and parent.is_displayed():
                    try:
                        scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", parent)
                        client_height = self.driver.execute_script("return arguments[0].clientHeight;", parent)
                        if scroll_height and client_height and scroll_height > client_height:
                            return parent
                    except Exception:
                        pass
        except Exception:
            pass
        return None
    
    def scroll_chat(self, direction: str = 'up') -> bool:
        """Focus message box then press Function Up or Down to scroll chat"""
        if not self.driver:
            raise Exception("Driver not initialized")
        # find message box and focus
        message_box = self._find_message_list_container()
        if message_box is None:
            message_box = self.driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]')
            if message_box is None:
                print(f"No message box found")
                return False
        message_box.click()
        time.sleep(0.1)
        # lookup scroll position 
        scroll_position = self.driver.execute_script("return arguments[0].scrollTop;", message_box)
        # press function up/down
        ActionChains(self.driver).send_keys(Keys.PAGE_UP if direction == 'up' else Keys.PAGE_DOWN).perform()
        time.sleep(0.1)
        # lookup scroll position
        new_scroll_position = self.driver.execute_script("return arguments[0].scrollTop;", message_box)
        scroll_amount = new_scroll_position - scroll_position
        if scroll_amount == 0:
            print(f"Chat did not scroll")
            return False
        print(f"Chat scrolled {scroll_amount} pixels")
        return True
    
    def get_visible_messages_simple(self, limit: int = 200) -> List[WhatsAppMessage]:
        """Simpler, robust collection of on-screen messages using message-in/out containers.

        - Select containers with classes containing 'message-in' or 'message-out'.
        - Read `data-pre-plain-text` from an element within each container to parse timestamp and sender.
        - Extract textual content from `span.selectable-text` descendants.
        
        - Reactions have an aria label like: "aria-label="reaction 👍. View reactions"" or "aria-label="Reactions 😂, 👍 2 in total. View reactions""
        
        - Images have a div with "aria-label="Open picture"" and a child like <img src="blob:https://web.whatsapp.com/4539aace-4b76-46e2-acdc-d3986239f348">
        """
        if not self.driver:
            raise Exception("Driver not initialized")
        
        containers = self.driver.find_elements(By.CSS_SELECTOR, 'div.message-in, div.message-out')
        
        print(f"Found {len(containers)} containers, limiting to {limit}")
        containers = containers[-limit:]
        
        msgs: List[WhatsAppMessage] = []
        chat_name = self._get_current_chat_name()
        for c in containers:
            try:
                # Determine direction from class
                is_outgoing = 'message-out' in (c.get_attribute('class') or '').lower()

                try:
                    # Parse meta
                    pre_elem = c.find_element(By.CSS_SELECTOR, '[data-pre-plain-text]')
                except Exception:
                    print(f"No pre-plain-text found for {c}")
                    continue

                ts, sender = parse_pre_plain_text(pre_elem.get_attribute('data-pre-plain-text') or '')
                
                if ts is None:
                    raise ValueError("Timestamp must not be None")
                
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
                    timestamp=ts,
                    is_outgoing=is_outgoing,
                    chat_name=chat_name,
                )
                msgs.append(message)
            except Exception as e:
                print(f"Error parsing message: {e}")
                continue
        return msgs

    def _locate_message_bubble(self, index_from_end: int = 1, incoming: Optional[bool] = None, text_contains: Optional[str] = None):
        """Locate a message bubble element by criteria.

        - index_from_end: 1 means latest, 2 means second latest, after filtering.
        - incoming: True for received, False for sent, None for either.
        - text_contains: case-insensitive substring to match inside the message text.
        """
        if not self.driver:
            raise Exception("Driver not initialized")
        
        try:
            selectors = [
                'div.message-in, div.message-out',
                '[data-testid="msg-container"]',
            ]

            candidates = []
            for sel in selectors:
                try:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    if elems:
                        candidates = elems
                        break
                except Exception:
                    continue

            if not candidates:
                return None

            def is_incoming(elem) -> Optional[bool]:
                try:
                    cls = (elem.get_attribute('class') or '').lower()
                    if 'message-in' in cls:
                        return True
                    if 'message-out' in cls:
                        return False
                except Exception:
                    pass
                return None

            # Filter by incoming/outgoing if requested
            filtered = []
            for c in candidates:
                if incoming is not None:
                    dirn = is_incoming(c)
                    if dirn is None or dirn != incoming:
                        continue
                if text_contains:
                    try:
                        content = extract_message_text_from_elem(c) or ''
                    except Exception:
                        content = (c.text or '')
                    if text_contains.lower() not in (content or '').lower():
                        continue
                filtered.append(c)

            if not filtered:
                filtered = candidates

            idx = -abs(index_from_end)
            if len(filtered) < abs(idx):
                return None
            return filtered[idx]
        except Exception:
            return None

    def react_to_message(self, emoji_query: str, index_from_end: int = 1, incoming: Optional[bool] = None, text_contains: Optional[str] = None, timeout: float = 6.0) -> bool:
        """Hover a message, open reactions, expand picker, search and select an emoji.

        emoji_query: e.g. "thumbs up", "heart", ":party:" or similar.
        """
        if not self.driver:
            raise Exception("Driver not initialized")
        
        try:
            bubble = self._locate_message_bubble(index_from_end=index_from_end, incoming=incoming, text_contains=text_contains)
            if not bubble:
                logger.error("Could not find target message bubble for reaction")
                return False

            # Hover to reveal reaction button
            try:
                ActionChains(self.driver).move_to_element(bubble).perform()
                time.sleep(0.25)
            except Exception:
                pass

            # Abort if there is already a reaction on this message
            try:
                existing_remove_btns = bubble.find_elements(By.XPATH, 
                    ".//button[normalize-space()='Click to remove' or contains(normalize-space(.), 'Click to remove')]"
                )
                if existing_remove_btns and any(btn.is_displayed() for btn in existing_remove_btns):
                    logger.info("Reaction already present on message; aborting react flow")
                    return True
            except Exception:
                pass

            wait = WebDriverWait(self.driver, timeout)

            def _find_first_displayed(scope, css_list):
                for css in css_list:
                    try:
                        elems = scope.find_elements(By.CSS_SELECTOR, css)
                        for e in elems:
                            if e and e.is_displayed():
                                return e
                    except Exception:
                        continue
                return None

            # Click reaction button (on hover toolbar)
            react_btn_selectors = [
                'button[aria-label*="React" i]',
                'div[role="button"][aria-label*="React" i]',
                '[data-testid*="react" i]',
                '[data-testid*="reactions" i]'
            ]

            react_btn = self._find_first_displayed(react_btn_selectors, scope=bubble) or self._find_first_displayed(react_btn_selectors)
            if not react_btn:
                # Try moving slightly inside bubble to trigger toolbar
                try:
                    ActionChains(self.driver).move_to_element_with_offset(bubble, 10, 10).perform()
                    time.sleep(0.25)
                    react_btn = _find_first_displayed(bubble, react_btn_selectors) or _find_first_displayed(self.driver, react_btn_selectors)
                except Exception:
                    pass

            if not react_btn:
                logger.error("Reaction button not found")
                return False

            self._click_element(react_btn)
            time.sleep(0.2)

            # Click "+" to open full emoji picker
            more_btn_selectors = [
                'button[aria-label*="More" i]',
                'div[role="button"][aria-label*="More" i]',
                'button[data-testid*="more" i]',
            ]

            def _wait_for_any(css_list, scope=None):
                scope_elem = scope or self.driver
                end = time.time() + timeout
                while time.time() < end:
                    el = _find_first_displayed(scope_elem, css_list)
                    if el:
                        return el
                    time.sleep(0.1)
                return None

            more_btn = self._wait_for_any(more_btn_selectors)
            if not more_btn:
                # Some builds show the full picker immediately; continue
                logger.debug("More reactions button not found; proceeding to search picker directly")
            else:
                self._click_element(more_btn)
                time.sleep(0.5)
            time.sleep(0.5)

            # Search field inside picker (explicit WhatsApp variant: aria-label="Search reaction")
            search_selectors = [
                'input[aria-label="Search reaction"]',
                'input[aria-label*="Search reaction" i]',
                'div[contenteditable="true"][aria-label*="Search reaction" i]',
            ]
            search = self._wait_for_any(search_selectors, scope=None)
            if search:
                try:
                    search.click()
                except Exception:
                    pass
                try:
                    search.clear()
                except Exception:
                    pass
                try:
                    search.send_keys(emoji_query)
                except Exception:
                    # Try contenteditable path
                    ActionChains(self.driver).send_keys(emoji_query).perform()
                # User requested: type -> wait 0.2s -> press Enter
                time.sleep(0.2)
                try:
                    ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                    time.sleep(0.2)
                    ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                    time.sleep(0.2)
                    return True
                except Exception:
                    pass

            # Select first result; some UIs render results as span[role="button"][data-emoji]
            result_selectors = [
                'div[role="grid"] [role="gridcell"] button',
                'div[role="grid"] button[role="option"]',
                'button[aria-label]',
                'span[role="button"][data-emoji]'
            ]
            result = (self._wait_for_any(result_selectors, scope=picker) if picker else None)
            if not result:
                logger.error("No emoji result selectable")
                return False

            # Try robust clicking strategies
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", result)
            except Exception:
                pass
            try:
                ActionChains(self.driver).move_to_element(result).pause(0.05).perform()
            except Exception:
                pass
            clicked = False
            for _ in range(3):
                try:
                    self.driver.execute_script("arguments[0].click();", result)
                    clicked = True
                    break
                except Exception:
                    try:
                        result.click()
                        clicked = True
                        break
                    except Exception:
                        try:
                            # Try clicking a closest clickable ancestor
                            ancestor = self.driver.execute_script("return arguments[0].closest && arguments[0].closest('button,[role=button]');", result)
                            if ancestor:
                                self.driver.execute_script("arguments[0].click();", ancestor)
                                clicked = True
                                break
                        except Exception:
                            time.sleep(0.05)
                            continue
            # If clicking the base emoji opened a variant (skin tone) chooser, click the first variant
            if clicked:
                try:
                    variant = _wait_for_any([
                        'div[role="menu"] button',
                        'div[role="menu"] [role="menuitem"]',
                        'div[role="dialog"] button[role="button"]',
                        'div[aria-label*="skin" i] button'
                    ])
                    if variant:
                        try:
                            self.driver.execute_script("arguments[0].click();", variant)
                        except Exception:
                            variant.click()
                        # Some UIs require an explicit confirm; send Enter to the focused variant
                        try:
                            variant.send_keys(Keys.RETURN)
                        except Exception:
                            pass
                        time.sleep(0.2)
                except Exception:
                    pass
            # Do not send global Enter as a fallback; avoid triggering chat search
            if not clicked:
                logger.error("Failed to click emoji result")
                return False
            time.sleep(0.3)
            return True
        except Exception as e:
            logger.error(f"Failed to react to message: {e}")
            return False

    def react_to_latest_incoming(self, emoji_query: str) -> bool:
        return self.react_to_message(emoji_query=emoji_query, incoming=True)

    def react_to_latest_outgoing(self, emoji_query: str) -> bool:
        return self.react_to_message(emoji_query=emoji_query, incoming=False)

    def react_to_message_containing(self, text_contains: str, emoji_query: str, incoming: Optional[bool] = None) -> bool:
        return self.react_to_message(emoji_query=emoji_query, text_contains=text_contains, incoming=incoming)

    def send_gif_by_search(self, query: str, press_enter_to_send: bool = True, timeout: float = 12.0) -> bool:
        """Open the GIF picker, search Tenor, select first result, optionally send.

        DOM guide hints:
        - Open panel via button with aria-label "Emojis, GIFs, Stickers"
        - Switch to GIFs via button with aria-label "Gifs selector"
        - Search box aria-label "Search GIFs via Tenor"
        - Then: Enter (search), ArrowDown (first), Enter (select), Enter (send)
        """
        if not self.driver:
            raise Exception("Driver not initialized")

        # Open the Emoji/GIFs/Stickers panel
        logger.info("GIF: opening panel")
        panel_btn_selectors = [
            '[aria-label="Emojis, GIFs, Stickers"]',
        ]
        btn = self._find_first_displayed(panel_btn_selectors)
        if not btn:
            raise NoSuchElementException("Emojis/GIFs/Stickers button not found")
        self._click_element(btn)
        logger.info("GIF: panel opened")
        time.sleep(0.3)

        # Switch to GIFs tab
        gifs_btn_selectors = [
            '[aria-label="Gifs selector"]',
        ]
        logger.info("GIF: locating GIFs tab")
        gifs_btn = self._find_first_displayed(gifs_btn_selectors)
        if not gifs_btn:
            raise NoSuchElementException("GIF button not found")
        
        self._click_element(gifs_btn)
        logger.info("GIF: switched to GIFs tab")
        time.sleep(0.3)

        # Search input inside the GIFs panel
        search_selectors = [
            'div[role="dialog"] input[aria-label="Search GIFs via Tenor"]',
            'div[role="dialog"] div[contenteditable="true"][aria-label*="Search GIFs" i]',
            'div[role="dialog"] [role="textbox"][aria-label*="Search GIFs" i]',
            'input[aria-label="Search GIFs via Tenor"]',
            'div[contenteditable="true"][aria-label*="Search GIFs" i]',
            '[role="textbox"][aria-label*="Search GIFs" i]'
        ]
        logger.info("GIF: waiting for Tenor search input")
        search_box = self._wait_for_any(search_selectors, timeout=timeout)

        if not search_box:
            raise NoSuchElementException("GIF search input not found")

        logger.info("GIF: focusing search input")
        self._focus_element(search_box)

        try:
            logger.info("GIF: clearing search input")
            search_box.clear()
        except Exception as e:
            logger.debug(f"GIF: clear failed: {e}")
        try:
            logger.info(f"GIF: typing query '{query}'")
            search_box.send_keys(query)
        except Exception as e:
            logger.debug(f"GIF: element send_keys failed ({e}); using ActionChains")
            ActionChains(self.driver).send_keys(query).perform()
        time.sleep(0.2)

        # Trigger search
        # try:
        #     logger.info("GIF: submit search via Enter")
        #     search_box.send_keys(Keys.RETURN)
        # except Exception as e:
        #     logger.debug(f"GIF: Enter via element failed ({e}); using ActionChains")
        #     ActionChains(self.driver).send_keys(Keys.RETURN).perform()

        # Prefer selecting via keyboard by focusing the first GIF button, else click it
        logger.info("GIF: waiting for first GIF result button")
        first_gif_btn = self._wait_for_any([
            'div[role="dialog"] button[type="button"][aria-label]',
            'div[role="dialog"] [role="button"][aria-label]',
            'button[type="button"][aria-label]'
        ], timeout=timeout)

        time.sleep(2)
        logger.info("GIF: sending arrow down key")
        ActionChains(self.driver).send_keys(Keys.ARROW_DOWN).perform()
        # search_box.send_keys(Keys.ARROW_DOWN)
        time.sleep(2)
        logger.info("GIF: sending return key")
        ActionChains(self.driver).send_keys(Keys.RETURN).perform()
        # search_box.send_keys(Keys.RETURN)
        time.sleep(1)
        logger.info("GIF: maybe sent?")
        ActionChains(self.driver).send_keys(Keys.RETURN).perform()
        time.sleep(1)
        # check if GIF menu still visible, if so send an Escape key press and return False
        if self._wait_for_any(['div[role="dialog"][aria-label*="GIFs" i]']):
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            return False
        return True

        
    def attach_media(self, file_paths: List[str], timeout: float = 12.0) -> bool:
        """Attach one or more images/videos to the current chat and send them.

        - Click the attach button (aria-label contains "Attach").
        - Locate hidden file input with accept including image/video.
        - Send absolute paths (joined with newline for multiple).
        - Press Enter to send once preview is attached.
        """
        if not self.driver:
            raise Exception("Driver not initialized")

        if not file_paths:
            raise ValueError("file_paths must not be empty")

        # Resolve and validate paths
        abs_paths: List[str] = []
        for p in file_paths:
            ap = os.path.abspath(p)
            if not os.path.exists(ap):
                raise FileNotFoundError(ap)
            abs_paths.append(ap)

        def _first_displayed(css_list: List[str], scope: Optional[WebElement] = None) -> Optional[WebElement]:
            s: Any = scope or self.driver
            if s is None:
                return None
            for css in css_list:
                try:
                    elems = s.find_elements(By.CSS_SELECTOR, css)
                    for e in elems:
                        if e and e.is_displayed():
                            return e
                except Exception:
                    continue
            return None

        # Click the attach button
        attach_btn_selectors = [
            'button[aria-label*="Attach" i]',
            'div[aria-label*="Attach" i]',
            'span[data-icon="clip"]',
        ]
        attach_btn = self._find_first_displayed(attach_btn_selectors)
        if attach_btn:
            try:
                self.driver.execute_script("arguments[0].click();", attach_btn)
            except Exception:
                attach_btn.click()
            time.sleep(0.2)

        # Find the file input which accepts images/videos
        end = time.time() + timeout
        file_input = None
        while time.time() < end and not file_input:
            try:
                candidates = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"][accept*="image"], input[type="file"][accept*="video"]')
                for el in candidates:
                    # Hidden inputs are acceptable for send_keys
                    if el.get_attribute('type') == 'file':
                        file_input = el
                        break
            except Exception:
                pass
            if not file_input:
                time.sleep(0.1)

        if not file_input:
            raise NoSuchElementException("File input for images/videos not found")

        files_value = "\n".join(abs_paths)
        file_input.send_keys(files_value)

        # Wait for media preview and try clicking the Send button within the preview
        time.sleep(0.5)
        end_send = time.time() + timeout
        sent = False
        while time.time() < end_send and not sent:
            try:
                # Common send buttons in media composer
                send_btn = self._find_first_displayed([
                    'button[aria-label="Send"]',
                    'button[data-testid="compose-btn-send"]',
                    'div[role="button"][aria-label="Send"]',
                ])
                if send_btn:
                    self._click_element(send_btn)
                    sent = True
                    break
            except Exception:
                pass
            time.sleep(0.1)

        if not sent:
            # Fallback: press Enter via keyboard without clicking the composer
            try:
                ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                sent = True
            except Exception:
                sent = False
            time.sleep(0.3)
        if not sent:
            return False
        return True

    def reply_to_message(self, reply_text: str, index_from_end: int = 1, incoming: Optional[bool] = None, text_contains: Optional[str] = None, timeout: float = 8.0) -> bool:
        """Reply to a specific message via the context menu then send text.

        - Hover the target message to reveal toolbar.
        - Open context menu (aria-label contains "Context menu").
        - Click the menu item labeled "Reply".
        - Type the reply and press Enter to send.
        """
        if not self.driver:
            raise Exception("Driver not initialized")

        bubble = self._locate_message_bubble(index_from_end=index_from_end, incoming=incoming, text_contains=text_contains)
        if not bubble:
            raise NoSuchElementException("Target message bubble not found")

        try:
            ActionChains(self.driver).move_to_element(bubble).perform()
            time.sleep(0.2)
        except Exception:
            pass

        def _first_displayed(css_list: List[str], scope: Optional[WebElement] = None) -> Optional[WebElement]:
            s: Any = scope or self.driver
            if s is None:
                return None
            for css in css_list:
                try:
                    elems = s.find_elements(By.CSS_SELECTOR, css)
                    for e in elems:
                        if e and e.is_displayed():
                            return e
                except Exception:
                    continue
            return None

        # Prefer clicking explicit Context menu button for reliability
        menu_btn = self._find_first_displayed(['[aria-label="Context menu"]'], scope=bubble)
        if not menu_btn:
            menu_btn = self._find_first_displayed(['[aria-label="Context menu"]'])
        if not menu_btn:
            # Fallback to right-click
            try:
                ActionChains(self.driver).context_click(bubble).perform()
                time.sleep(0.2)
            except Exception:
                raise NoSuchElementException("Context menu control not found")
        else:
            self._click_element(menu_btn)
            time.sleep(0.2)

        # Click the "Reply" menu item
        end = time.time() + timeout
        clicked_reply = False
        while time.time() < end and not clicked_reply:
            try:
                # Look within common menu containers first
                xpath = (
                    "//div[@role='menu']//span[normalize-space(.)='Reply'] | "
                    "//div[@role='menu']//div[normalize-space(.)='Reply'] | "
                    "//span[normalize-space(.)='Reply'] | //div[normalize-space(.)='Reply']"
                )
                reply_item = self.driver.find_element(By.XPATH, xpath)
                if reply_item and reply_item.is_displayed():
                    self.driver.execute_script("arguments[0].click();", reply_item)
                    clicked_reply = True
                    break
            except Exception:
                pass
            time.sleep(0.1)
        if not clicked_reply:
            raise NoSuchElementException("Reply menu item not found")

        # Type and send reply
        box = self.focus_message_box()
        if not box:
            return False
        try:
            box.clear()
        except Exception:
            pass
        try:
            pyperclip.copy(reply_text)
            box.send_keys(CONTROL_KEY, 'v')
        except Exception:
            box.send_keys(reply_text)
        box.send_keys(Keys.RETURN)
        time.sleep(0.3)
        return True

    def reply_to_message_containing(self, contains_text: str, reply_text: str, incoming: Optional[bool] = None, timeout: float = 8.0) -> bool:
        """Find a message containing a substring and reply to it.

        contains_text: case-insensitive substring to find in a message bubble.
        incoming: True/False to restrict direction; None for either.
        """
        return self.reply_to_message(
            reply_text=reply_text,
            index_from_end=1,
            incoming=incoming,
            text_contains=contains_text,
            timeout=timeout,
        )

    def simulate_typing_indicator(self, duration_sec: float = 2.0) -> bool:
        """Simulate typing indicator by entering text ("..."), waiting, then clearing without sending."""
        if not self.driver:
            raise Exception("Driver not initialized")
        if duration_sec < 0:
            raise ValueError("duration_sec must be non-negative")
        box = self.focus_message_box()
        if not box:
            return False
        try:
            box.click()
        except Exception:
            pass
        try:
            box.send_keys("...")
        except Exception:
            ActionChains(self.driver).send_keys("...").perform()
        time.sleep(duration_sec)
        try:
            ActionChains(self.driver).key_down(CONTROL_KEY).send_keys('a').key_up(CONTROL_KEY).send_keys(Keys.DELETE).perform()
        except Exception:
            # Fallback: backspace the same number of characters
            for _ in range(3):
                try:
                    box.send_keys(Keys.BACK_SPACE)
                except Exception:
                    break
        time.sleep(0.1)
        return True

    def list_recent_chat_entries(self, max_rows: int = 30, max_scrolls: int = 40, search_term: Optional[str] = None) -> List[ChatListEntry]:
        """Return structured recent chat entries with name, preview, and time.

        - Name selector: within the chat grid cell col 2, `span[title]`.
        - Preview selector: within the same row, `span[dir="ltr"]:not([title])`.
        - Time selector: sibling `div._ak8i` (as seen in provided HTML), fallback to any time-like cell.
        """
        if not self.driver:
            raise Exception("Driver not initialized")
        
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
                if not preview:
                    preview = "NO PREVIEW"
                if not time_text:
                    time_text = "NO TIME TEXT"
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

if __name__ == "__main__":
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    