"""Configuration management for WhatsApp automation tool (Anthropic-only)."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    # API Keys
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    # WhatsApp Configuration
    chrome_profile_path: str = Field(default="", description="Path to Chrome profile directory")
    signup_my_name: str = Field(default="", description="Display name used when auto-signing up")
    # LLM Configuration
    anthropic_model: str = Field(default="claude-sonnet-4-20250514")
    max_tokens: int = Field(default=1000)
    temperature: float = Field(default=0.7)
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/whatsapp_automation.log")
    
    def validate_api_keys(self) -> bool:
        """Validate that Anthropic API key is provided."""
        return bool(self.anthropic_api_key)

# Global settings instance
settings = Settings() 