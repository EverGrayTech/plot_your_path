"""Tests for the LLM service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config import LLMConfig
from backend.services.llm_service import LLMError, LLMService


@pytest.fixture
def openai_config():
    """OpenAI LLM config for testing."""
    return LLMConfig(provider="openai", model="gpt-4o", api_key_env="OPENAI_API_KEY")


@pytest.fixture
def anthropic_config():
    """Anthropic LLM config for testing."""
    return LLMConfig(
        provider="anthropic", model="claude-3-sonnet", api_key_env="ANTHROPIC_API_KEY"
    )


@pytest.fixture
def ollama_config():
    """Ollama LLM config for testing."""
    return LLMConfig(provider="ollama", model="llama3", api_key_env="OPENAI_API_KEY")


SAMPLE_JOB_MARKDOWN = """
# Senior Software Engineer - Backend

**Company:** Acme Corp
**Team:** Platform Engineering
**Salary:** $150,000 - $200,000 USD

## Requirements
- 5+ years of Python experience
- Experience with FastAPI or Django
- PostgreSQL and database design
- Docker and Kubernetes (preferred)
- Strong communication skills

## Nice to Have
- Experience with Rust
- Open source contributions
"""

SAMPLE_LLM_JSON_RESPONSE = json.dumps({
    "title": "Senior Software Engineer - Backend",
    "company": "Acme Corp",
    "team_division": "Platform Engineering",
    "salary_min": 150000,
    "salary_max": 200000,
    "salary_currency": "USD",
    "required_skills": ["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "Communication"],
    "preferred_skills": ["Kubernetes", "Rust"],
})


class TestOpenAIProvider:
    """Tests for OpenAI integration."""

    @pytest.mark.asyncio
    async def test_call_openai_success(self, openai_config, monkeypatch):
        """Test successful OpenAI API call."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=openai_config)

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Hello from OpenAI"

        with patch("openai.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await service._call_openai("Test prompt")
            assert result == "Hello from OpenAI"

    @pytest.mark.asyncio
    async def test_call_openai_failure(self, openai_config, monkeypatch):
        """Test OpenAI API failure raises LLMError."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=openai_config)

        with patch("openai.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMError, match="OpenAI API call failed"):
                await service._call_openai("Test prompt")


class TestAnthropicProvider:
    """Tests for Anthropic integration."""

    @pytest.mark.asyncio
    async def test_call_anthropic_success(self, anthropic_config, monkeypatch):
        """Test successful Anthropic API call."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        service = LLMService(config=anthropic_config)

        mock_text_block = MagicMock()
        mock_text_block.text = "Hello from Anthropic"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await service._call_anthropic("Test prompt")
            assert result == "Hello from Anthropic"

    @pytest.mark.asyncio
    async def test_call_anthropic_failure(self, anthropic_config, monkeypatch):
        """Test Anthropic API failure raises LLMError."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        service = LLMService(config=anthropic_config)

        with patch("anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMError, match="Anthropic API call failed"):
                await service._call_anthropic("Test prompt")


class TestOllamaProvider:
    """Tests for Ollama integration."""

    @pytest.mark.asyncio
    async def test_call_ollama_success(self, ollama_config, monkeypatch):
        """Test successful Ollama API call."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=ollama_config)

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Hello from Ollama"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service._call_ollama("Test prompt")
            assert result == "Hello from Ollama"

    @pytest.mark.asyncio
    async def test_call_ollama_failure(self, ollama_config, monkeypatch):
        """Test Ollama API failure raises LLMError."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=ollama_config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(LLMError, match="Ollama API call failed"):
                await service._call_ollama("Test prompt")


class TestComplete:
    """Tests for the complete() method."""

    @pytest.mark.asyncio
    async def test_complete_routes_to_openai(self, openai_config, monkeypatch):
        """Test that complete() routes to OpenAI for openai provider."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=openai_config)
        service._call_openai = AsyncMock(return_value="OpenAI response")

        result = await service.complete("test prompt")
        assert result == "OpenAI response"
        service._call_openai.assert_called_once_with("test prompt")

    @pytest.mark.asyncio
    async def test_complete_routes_to_anthropic(self, anthropic_config, monkeypatch):
        """Test that complete() routes to Anthropic for anthropic provider."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        service = LLMService(config=anthropic_config)
        service._call_anthropic = AsyncMock(return_value="Anthropic response")

        result = await service.complete("test prompt")
        assert result == "Anthropic response"
        service._call_anthropic.assert_called_once_with("test prompt")

    @pytest.mark.asyncio
    async def test_complete_routes_to_ollama(self, ollama_config, monkeypatch):
        """Test that complete() routes to Ollama for ollama provider."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=ollama_config)
        service._call_ollama = AsyncMock(return_value="Ollama response")

        result = await service.complete("test prompt")
        assert result == "Ollama response"
        service._call_ollama.assert_called_once_with("test prompt")

    @pytest.mark.asyncio
    async def test_complete_invalid_provider(self):
        """Test that invalid provider raises ValueError."""
        config = LLMConfig(api_key_env="OPENAI_API_KEY")
        config.provider = "invalid"  # type: ignore
        service = LLMService(config=config)

        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            await service.complete("test prompt")


class TestDenoise:
    """Tests for job posting de-noising."""

    @pytest.mark.asyncio
    async def test_denoise_job_posting(self, openai_config, monkeypatch):
        """Test that denoise returns clean markdown."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=openai_config)
        service.complete = AsyncMock(return_value="# Job Title\n\nDescription here")

        result = await service.denoise_job_posting("Raw messy HTML text here")
        assert result == "# Job Title\n\nDescription here"
        service.complete.assert_called_once()


class TestExtractJobData:
    """Tests for structured job data extraction."""

    @pytest.mark.asyncio
    async def test_extract_job_data_success(self, openai_config, monkeypatch):
        """Test successful job data extraction."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=openai_config)
        service.complete = AsyncMock(return_value=SAMPLE_LLM_JSON_RESPONSE)

        result = await service.extract_job_data(SAMPLE_JOB_MARKDOWN)
        assert result["title"] == "Senior Software Engineer - Backend"
        assert result["company"] == "Acme Corp"
        assert "Python" in result["required_skills"]
        assert "Kubernetes" in result["preferred_skills"]
        assert result["salary_min"] == 150000

    @pytest.mark.asyncio
    async def test_extract_strips_code_fences(self, openai_config, monkeypatch):
        """Test that JSON code fences are stripped."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=openai_config)
        service.complete = AsyncMock(
            return_value=f"```json\n{SAMPLE_LLM_JSON_RESPONSE}\n```"
        )

        result = await service.extract_job_data(SAMPLE_JOB_MARKDOWN)
        assert result["title"] == "Senior Software Engineer - Backend"

    @pytest.mark.asyncio
    async def test_extract_raises_on_invalid_json(self, openai_config, monkeypatch):
        """Test that invalid JSON raises LLMError."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=openai_config)
        service.complete = AsyncMock(return_value="This is not JSON at all")

        with pytest.raises(LLMError, match="LLM returned invalid JSON"):
            await service.extract_job_data(SAMPLE_JOB_MARKDOWN)

    @pytest.mark.asyncio
    async def test_extract_raises_on_missing_field(self, openai_config, monkeypatch):
        """Test that missing required field raises LLMError."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        service = LLMService(config=openai_config)
        # Missing 'required_skills' field
        incomplete_json = json.dumps({
            "title": "Engineer",
            "company": "Acme",
            "preferred_skills": [],
        })
        service.complete = AsyncMock(return_value=incomplete_json)

        with pytest.raises(LLMError, match="missing required field"):
            await service.extract_job_data(SAMPLE_JOB_MARKDOWN)
