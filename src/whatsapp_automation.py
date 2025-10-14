"""Simplified WhatsApp Web automation using Selenium."""
import time
import os
import asyncio
from typing import List, Optional, Tuple
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
from selenium.webdriver.remote.webelement import WebElement
from pydantic import BaseModel

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
    
    def focus_chat_list_search(self) -> Optional[WebElement]:
        """Focus the chat list search."""
        """The chat list search always has the following aria-label"""
        """aria-label="Search input textbox"""
        
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
        
        # Find aria label starting "Type to"... and extract the chat name
        try:
            aria_label = self.driver.find_element(By.CSS_SELECTOR, 'div[aria-label^="Type to"]').get_attribute('aria-label')
        except:
            logger.info("Did not finnd an open chat.")
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
            logger.error("Failed to get extra info from title element.")
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
        message_box.send_keys(message)
        message_box.send_keys(Keys.RETURN)
        time.sleep(0.5)
        return True

    def get_recent_messages(self, limit: int = 10) -> List[WhatsAppMessage]:
        """Get recent messages from current chat."""
        # This is to be deprecated in favour of the more general get_visible_messages_simple
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
        ActionChains(self.driver).send_keys(Keys.PAGE_UP if direction == 'up' else Keys.PAGE_).perform()
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

    def _locate_message_bubble(self, index_from_end: int = 1, incoming: Optional[bool] = None, text_contains: Optional[str] = None):
        """Locate a message bubble element by criteria.

        - index_from_end: 1 means latest, 2 means second latest, after filtering.
        - incoming: True for received, False for sent, None for either.
        - text_contains: case-insensitive substring to match inside the message text.
        """
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

            react_btn = _find_first_displayed(bubble, react_btn_selectors) or _find_first_displayed(self.driver, react_btn_selectors)
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

            try:
                self.driver.execute_script("arguments[0].click();", react_btn)
            except Exception:
                react_btn.click()
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

            more_btn = _wait_for_any(more_btn_selectors)
            if not more_btn:
                # Some builds show the full picker immediately; continue
                logger.debug("More reactions button not found; proceeding to search picker directly")
            else:
                try:
                    self.driver.execute_script("arguments[0].click();", more_btn)
                except Exception:
                    more_btn.click()
                time.sleep(0.5)
            time.sleep(0.5)
            # Emoji picker panel
            picker_selectors = [
                'div[data-testid="emoji-picker"]',
                'div[data-testid="emoji-panel"]',
                'div[role="dialog"][aria-label*="Emoji" i]'
            ]
            picker = _wait_for_any(picker_selectors)
            if not picker:
                logger.debug("Emoji picker container not detected; proceeding to search globally")

            # Search field inside picker (explicit WhatsApp variant: aria-label="Search reaction")
            search_selectors = [
                'input[aria-label="Search reaction"]',
                'input[aria-label*="Search reaction" i]',
                'div[contenteditable="true"][aria-label*="Search reaction" i]',
                'input[aria-label*="Search" i]',
                'input[placeholder*="Search" i]',
                'div[contenteditable="true"]'
            ]
            search = _wait_for_any(search_selectors, scope=picker) if picker else _wait_for_any(search_selectors)
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
                    return True
                except Exception:
                    pass
            else:
                # Focus may already be inside the picker; try active element, then global typing
                try:
                    active = self.driver.switch_to.active_element
                    try:
                        active.send_keys(emoji_query)
                    except Exception:
                        ActionChains(self.driver).send_keys(emoji_query).perform()
                    # User requested: type -> wait 0.2s -> press Enter
                    time.sleep(0.2)
                    try:
                        ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                        time.sleep(0.2)
                        return True
                    except Exception:
                        pass
                except Exception:
                    pass

            # Select first result; some UIs render results as span[role="button"][data-emoji]
            result_selectors = [
                'div[role="grid"] [role="gridcell"] button',
                'div[role="grid"] button[role="option"]',
                'button[aria-label]',
                'span[role="button"][data-emoji]'
            ]
            result = (_wait_for_any(result_selectors, scope=picker) if picker else _wait_for_any(result_selectors)) or _wait_for_any(['span[role="button"][data-emoji]'])
            if not result:
                # As fallback, press Enter to pick first suggestion
                try:
                    ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                    time.sleep(0.3)
                    return True
                except Exception:
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
            if not clicked:
                try:
                    # Final fallback: press Enter which often selects the first suggestion
                    ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                    time.sleep(0.2)
                    clicked = True
                except Exception:
                    pass
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

if __name__ == "__main__":
    automation = WhatsAppAutomation()
    asyncio.run(automation.start())
    