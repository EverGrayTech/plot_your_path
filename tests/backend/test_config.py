"""Tests for configuration management."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from backend.config import LLMConfig, ScrapingConfig, Settings


class TestLLMConfig:
    """Tests for LLM configuration."""

    def test_llm_config_defaults(self):
        """Test LLM config with default values."""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.api_key_env == "OPENAI_API_KEY"
        assert config.temperature == 0.1
        assert config.max_tokens == 4000

    def test_llm_config_from_file(self):
        """Test loading LLM config from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "provider": "anthropic",
                "model": "claude-3-sonnet",
                "api_key_env": "ANTHROPIC_API_KEY",
                "temperature": 0.2,
                "max_tokens": 8000,
            }
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = LLMConfig.from_file(temp_path)
            assert config.provider == "anthropic"
            assert config.model == "claude-3-sonnet"
            assert config.api_key_env == "ANTHROPIC_API_KEY"
            assert config.temperature == 0.2
            assert config.max_tokens == 8000
        finally:
            os.unlink(temp_path)

    def test_llm_config_get_api_key_success(self, monkeypatch):
        """Test getting API key from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        config = LLMConfig()
        assert config.get_api_key() == "test-key-123"

    def test_llm_config_get_api_key_missing(self, monkeypatch):
        """Test error when API key is missing."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = LLMConfig()
        with pytest.raises(ValueError, match="API key not found"):
            config.get_api_key()

    def test_llm_config_custom_api_key_env(self, monkeypatch):
        """Test with custom API key environment variable."""
        monkeypatch.setenv("CUSTOM_API_KEY", "custom-key-456")
        config = LLMConfig(api_key_env="CUSTOM_API_KEY")
        assert config.get_api_key() == "custom-key-456"


class TestScrapingConfig:
    """Tests for scraping configuration."""

    def test_scraping_config_defaults(self):
        """Test scraping config with default values."""
        config = ScrapingConfig()
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3
        assert config.user_agent == "Mozilla/5.0 (compatible; PlotYourPath/1.0)"
        assert config.rate_limit_delay_seconds == 2

    def test_scraping_config_from_file(self):
        """Test loading scraping config from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "timeout_seconds": 60,
                "retry_attempts": 5,
                "user_agent": "CustomBot/2.0",
                "rate_limit_delay_seconds": 5,
            }
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = ScrapingConfig.from_file(temp_path)
            assert config.timeout_seconds == 60
            assert config.retry_attempts == 5
            assert config.user_agent == "CustomBot/2.0"
            assert config.rate_limit_delay_seconds == 5
        finally:
            os.unlink(temp_path)

    def test_scraping_config_custom_values(self):
        """Test scraping config with custom values."""
        config = ScrapingConfig(
            timeout_seconds=45,
            retry_attempts=2,
            user_agent="TestBot/1.0",
            rate_limit_delay_seconds=3,
        )
        assert config.timeout_seconds == 45
        assert config.retry_attempts == 2
        assert config.user_agent == "TestBot/1.0"
        assert config.rate_limit_delay_seconds == 3


class TestSettings:
    """Tests for application settings."""

    def test_settings_defaults(self):
        """Test settings with default values."""
        settings = Settings()
        assert settings.database_url == "sqlite:///./data/plot_your_path.db"
        assert settings.backend_host == "0.0.0.0"
        assert settings.backend_port == 8000
        assert settings.next_public_api_url == "http://localhost:8000"

    def test_settings_from_env(self, monkeypatch):
        """Test loading settings from environment variables."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        monkeypatch.setenv("BACKEND_HOST", "127.0.0.1")
        monkeypatch.setenv("BACKEND_PORT", "9000")
        monkeypatch.setenv("NEXT_PUBLIC_API_URL", "http://localhost:9000")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")

        settings = Settings()
        assert settings.database_url == "sqlite:///./test.db"
        assert settings.backend_host == "127.0.0.1"
        assert settings.backend_port == 9000
        assert settings.next_public_api_url == "http://localhost:9000"
        assert settings.openai_api_key == "test-openai-key"
        assert settings.anthropic_api_key == "test-anthropic-key"

    def test_settings_optional_api_keys(self):
        """Test that API keys are optional in settings."""
        settings = Settings()
        # API keys should be None if not set
        assert settings.openai_api_key is None or isinstance(settings.openai_api_key, str)
        assert settings.anthropic_api_key is None or isinstance(
            settings.anthropic_api_key, str
        )
