"""LLM client for generating responses using the Anthropic API."""

from typing import Optional
from anthropic.types import Message, MessageParam, TextBlockParam, TextBlock, ToolUseBlock
from abc import ABC, abstractmethod
import anthropic
from loguru import logger
from src.schemas import WhatsAppMessage
from src.config import settings
import asyncio
from dataclasses import dataclass

@dataclass
class ErrorResponse:
    error_message: str

@dataclass
class SkipResponse:
    pass

@dataclass
class ReactResponse:
    message_to_react: str
    emoji_name: str

@dataclass
class GifResponse:
    search_term: str

@dataclass
class MessageResponse:
    text: str

LLMResponse = SkipResponse | ReactResponse | MessageResponse | ErrorResponse

class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @property
    @abstractmethod
    def skip_tool(self) -> dict:
        """Tool definition for skipping responses."""
        # make sure included in tool call api
        pass

    @property
    @abstractmethod
    def react_tool(self) -> dict:
        """Tool definition for reacting to messages."""
        # make sure included in tool call api
        pass

    @abstractmethod
    async def generate_react_response(
        self, 
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> SkipResponse | ReactResponse | ErrorResponse:
        """Generate a response with react and skip tool."""
        pass

    @abstractmethod
    async def generate_response(
        self, 
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        allow_skip: bool = True
    ) -> LLMResponse:
        """Generate a response with only skip tool."""
        pass
    
    @abstractmethod
    async def complete_message(self, message: str, system=None) -> str:
        """Complete a message using the LLM client."""
        pass

class AnthropicClient(LLMClient):
    """Anthropic API client."""

    @property
    def skip_tool(self) -> dict:
        """Tool definition for skipping responses."""
        return {
            "name": "skip",
            "description": "Use this tool to skip response, but only if that would be the most natural thing to do, which would not often be the case.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    
    @property
    def react_tool(self) -> dict:
        """Tool definition for reacting to messages."""
        return {
            "name": "react",
            "description": "Use this tool liberally to react to a Whatsapp message with an emoji.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message_to_react": {
                        "type": "string",
                        "description": "The exact text content of the message to react to."
                    },
                    "emoji_name": {
                        "type": "string",
                        "description": "The name of the emoji to react with, e.g. 'thumbs up', 'smile', 'heart'. This should be a short search term with just spaces and letters that will return the desired emoji."
                    }
                },
                "required": ["message_to_react", "emoji_name"]
            }
        }
    
    @property
    def gif_tool(self) -> dict:
        """Tool definition for sending GIFs."""
        return {
            "name": "send_gif",
            "description": "Use this tool to send a GIF in response to a message.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "The search term to find an appropriate GIF."
                    }
                },
                "required": ["search_term"]
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
        blocks = response.content
        for block in blocks:
            if isinstance(block, TextBlock):
                return block.text
        raise ValueError("No text block found in response from anthropic API.")

    async def generate_response(
        self, 
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        allow_skip: bool = True
    ) -> LLMResponse:
        """Generate a response WITHOUT react tools."""
        return (await self.generate_responses(
            messages,
            system_prompt,
            allow_skip
        ))[0]

    async def generate_react_response(
        self, 
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> ReactResponse | ErrorResponse | SkipResponse:
        """Generate a response with reaction tool."""
        llm_response = (await self.generate_responses(
            messages,
            system_prompt,
            allow_skip=True,
            allow_react=True,
            allow_gif=True,
            tool_choice="any"
        ))[0]
        if isinstance(llm_response, MessageResponse):
            raise ValueError("generate react reesponse gennerated a message instead")
        return llm_response
    
# When working with the tool_choice parameter, we have four possible options:
# auto allows Claude to decide whether to call any provided tools or not. This is the default value when tools are provided.
# any tells Claude that it must use one of the provided tools, but doesn’t force a particular tool.
# tool allows us to force Claude to always use a particular tool.
# none prevents Claude from using any tools. This is the default value when no tools are provided.

    async def generate_responses(
        self, 
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        allow_skip: bool = True,
        allow_react: bool = False,
        allow_gif: bool = False,
        tool_choice: str = "auto"
    ) -> list[LLMResponse]:
        """Generate responses with choice of tools."""
        extra_params = {}
        if system_prompt:
            extra_params["system"] = system_prompt
        extra_params["tool_choice"] = {"type": tool_choice}
        if allow_skip or allow_react or allow_gif:
            extra_params["tools"] = []
            if allow_skip:
                extra_params["tools"].append(self.skip_tool)
            if allow_react:
                extra_params["tools"].append(self.react_tool)
            if allow_gif:
                extra_params["tools"].append(self.gif_tool)

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            if msg["role"] in ["user", "assistant"]:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        try:
            # Use Messages API (recommended by Anthropic)
            response: Message = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                messages=anthropic_messages,
                **extra_params
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

        # Check if response has content
        if not response.content or len(response.content) == 0:
            logger.error("Anthropic API returned empty content")
            return [ErrorResponse(error_message="Anthropic API returned empty content")]

        # Handle different content types
        responses = []
        for content_block in response.content:
            if len(response.content) > 1:
                print(response)
            if content_block.type == "text":
                assert isinstance(content_block, TextBlock)
                responses.append(MessageResponse(text=content_block.text.strip()))
            elif content_block.type == "tool_use" and content_block.name == "skip":
                assert isinstance(content_block, ToolUseBlock)
                logger.info("LLM chose to skip response")
                responses.append(SkipResponse())
            elif content_block.type == "tool_use" and content_block.name == "react":
                assert isinstance(content_block, ToolUseBlock)
                inputs:dict = content_block.input  # type: ignore
                if "message_to_react" in inputs and "emoji_name" in inputs:
                    react_response = ReactResponse(
                        message_to_react=inputs["message_to_react"],
                        emoji_name=inputs["emoji_name"]
                        )
                    responses.append(react_response)
            elif content_block.type == "tool_use" and content_block.name == "send_gif":
                inputs:dict = content_block.input  # type: ignore
                if "search_term" in inputs:
                    gif_response = GifResponse(
                        search_term=inputs["search_term"]
                    )
                    responses.append(gif_response)

        if len(responses) == 0:
            # If we get here, no text or skip tool was found
            logger.warning("No valid content found in response")
            responses.append(ErrorResponse(error_message="No valid content found in response"))
        
        return responses

class LLMManager:
    """Manager class for LLM operations."""
    
    def __init__(self):
        self.client = self._create_client()
    
    def _create_client(self) -> LLMClient:
        """Create the Anthropic LLM client."""
        return AnthropicClient()
    
    async def complete_message(self, message: str, system: Optional[str] = None) -> str:
        """Complete a message using the LLM client."""
        return await self.client.complete_message(message, system)
    
    async def generate_response(
        self, 
        messages: list[dict[str, str]], 
        system_prompt: Optional[str] = None,
        allow_skip: bool = True
    ) -> LLMResponse:
        """Generate a response using the LLM client."""
        return await self.client.generate_response(messages, system_prompt, allow_skip)
    
    async def generate_react_response(
        self, 
        messages: list[dict[str, str]], 
        system_prompt: Optional[str] = None,
    ) -> ReactResponse | ErrorResponse | SkipResponse:
        """Generate a react response using the LLM client."""
        return await self.client.generate_react_response(messages, system_prompt)

    async def generate_whatsapp_chatter_response(
        self,
        messages: list[WhatsAppMessage],
    ) -> str:
        """Generate a response using the LLM client."""
        system_prompt = f"""You are {settings.user_name}, replying on WhatsApp.
        - Use the conversation history for context, try to emulate the style of your previous messages as closely as possible.
        - Each line includes the speaker for information, but only output the message.
        - Reply to the MOST RECENT user's message specifically.
        - Be very brief, no more than 20 words, and informal.
        - Avoid multi-paragraph messages.
        - Do not include meta text (like "friendly reply"). Only output the message you would send."""
        new_messages = []
        for message in messages:
            new_messages.append({
                "role": "user" if not message.is_outgoing else "assistant",
                "content": f"{message.sender}: {message.content}"
            })
        llm_response = await self.client.generate_response(new_messages, system_prompt)
        if isinstance(llm_response, MessageResponse):
            return llm_response.text
        
        raise ValueError("generating response failed to produce a MessageResponse")