"""LLM client for generating responses using the Anthropic API."""

from typing import Optional, List, Dict
from abc import ABC, abstractmethod
import anthropic
from loguru import logger

from config import settings

class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
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

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
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
            )
            return response.content[0].text.strip()
            
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
    
    async def generate_whatsapp_response(
        self, 
        incoming_message: str,
        sender_name: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """Generate a WhatsApp response based on incoming message and context."""
        
        system_prompt = f"""You are {settings.signup_my_name}, replying on WhatsApp.
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