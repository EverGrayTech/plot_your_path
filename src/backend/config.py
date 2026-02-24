"""Configuration management for the application."""

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration."""

    provider: Literal["openai", "anthropic", "ollama"] = "openai"
    model: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = 0.1
    max_tokens: int = 4000

    @classmethod
    def from_file(cls, filepath: str = "config/llm.json") -> "LLMConfig":
        """
        Load LLM configuration from JSON file.
        
        Args:
            filepath: Path to the configuration file
            
        Returns:
            LLMConfig instance
        """
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls(**data)

    def get_api_key(self) -> str:
        """
        Get the API key from environment variable.
        
        Returns:
            API key string
            
        Raises:
            ValueError: If API key environment variable is not set
        """
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(
                f"API key not found. Please set {self.api_key_env} environment variable."
            )
        return api_key


class ScrapingConfig(BaseSettings):
    """Web scraping configuration."""

    timeout_seconds: int = 30
    retry_attempts: int = 3
    user_agent: str = "Mozilla/5.0 (compatible; PlotYourPath/1.0)"
    rate_limit_delay_seconds: int = 2

    @classmethod
    def from_file(cls, filepath: str = "config/scraping.json") -> "ScrapingConfig":
        """
        Load scraping configuration from JSON file.
        
        Args:
            filepath: Path to the configuration file
            
        Returns:
            ScrapingConfig instance
        """
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls(**data)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(default="sqlite:///./data/plot_your_path.db")

    # Backend Server
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)

    # Frontend
    next_public_api_url: str = Field(default="http://localhost:8000")

    # API Keys (optional, loaded from env)
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)


# Global settings instance
settings = Settings()

# Load configurations
llm_config = LLMConfig.from_file()
scraping_config = ScrapingConfig.from_file()
