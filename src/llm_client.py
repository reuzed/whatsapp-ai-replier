"""LLM client for generating responses using the Anthropic API."""

from typing import Optional, List, Dict
from abc import ABC, abstractmethod
import anthropic
from loguru import logger
from src.schemas import WhatsAppMessage
from src.config import settings
import asyncio

class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @property
    @abstractmethod
    def skip_tool(self) -> dict:
        """Tool definition for skipping responses."""
        # make sure included in tool call api
        pass

    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate a response from the LLM."""
        pass

class AnthropicClient(LLMClient):
    """Anthropic API client."""

    @property
    def skip_tool(self) -> dict:
        """Tool definition for skipping responses."""
        return {
            "name": "skip",
            "description": "Use this tool to skip response.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        
    async def complete_message(self, message: str, system=None) -> str:
        """Complete a message using Anthropic's API."""
        response = await self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            system=system or "You are a helpful WhatsApp assistant.",
            messages=[{
                "role": "user",
                "content": message
            }]
        )
        print(response.content[0].text)
        return response.content[0].text

    async def generate_response(
        self, 
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate a response using Anthropic's API."""
        try:
            # Convert messages to Anthropic format
            anthropic_messages = []
            for msg in messages:
                if msg["role"] in ["user", "assistant"]:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Use Messages API (recommended by Anthropic)
            response = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                system=system_prompt or "You are a helpful assistant.",
                messages=anthropic_messages,
                tools=[self.skip_tool],
            )

            # Check if response has content
            if not response.content or len(response.content) == 0:
                logger.error("Anthropic API returned empty content")
                return ""
            
            # Handle different content types
            for content_block in response.content:
                if content_block.type == "text":
                    return content_block.text.strip()
                elif content_block.type == "tool_use" and content_block.name == "skip":
                    logger.info("LLM chose to skip response")
                    return ""  # Return empty string to indicate no response
            
            # If we get here, no text or skip tool was found
            logger.warning("No valid content found in response")
            return ""
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

class LLMManager:
    """Manager class for LLM operations."""
    
    def __init__(self):
        self.client = self._create_client()
    
    def _create_client(self) -> LLMClient:
        """Create the Anthropic LLM client."""
        return AnthropicClient()
    
    def complete_message(self, message: str, system: Optional[str] = None) -> str:
        """Complete a message using the LLM client."""
        return self.client.complete_message(message, system)
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate a response using the LLM client."""
        return await self.client.generate_response(messages, system_prompt)
    
    async def generate_whatsapp_response(
        self, 
        incoming_message: str,
        sender_name: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """Generate a WhatsApp response based on incoming message and context."""
        
        system_prompt = f"""You are {settings.user_name}, replying on WhatsApp.
        - Use the conversation history for context.
        - Each line includes the speaker for information, but only output the message.
        - Reply to the MOST RECENT user's message specifically.
        - Be very brief, no more than 20 words, and informal.
        - Avoid multi-paragraph messages.
        - Do not include meta text (like "friendly reply"). Only output the message you would send."""

        messages = conversation_history or []
        messages.append({
            "role": "user", 
            "content": f"From {sender_name}: {incoming_message}"
        })
        
        return await self.client.generate_response(messages, system_prompt)
    
    async def generate_whatsapp_chatter_response(
        self,
        messages: list[WhatsAppMessage],
    ) -> str:
        """Generate a response using the LLM client."""
        system_prompt = f"""You are {settings.user_name}, replying on WhatsApp.
        - Use the conversation history for context.
        - Each line includes the speaker for information, but only output the message.
        - Reply to the MOST RECENT user's message specifically.
        - Be very brief, no more than 20 words, and informal.
        - Avoid multi-paragraph messages.
        - Do not include meta text (like "friendly reply"). Only output the message you would send."""
        messages = []
        for message in messages:
            messages.append({
                "role": "user" if not message.is_outgoing else "assistant",
                "content": f"{message.sender}: {message.content}"
            })
        return await self.client.generate_response(messages, system_prompt)