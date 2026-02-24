"""LLM service for job posting processing with multi-provider support."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.config import LLMConfig

# Prompts
DENOISE_PROMPT = """You are a job posting parser. Convert the following raw text extracted from a job posting webpage into clean, well-structured Markdown.

Rules:
- Preserve all relevant job information (title, company, team, salary, requirements, responsibilities, etc.)
- Remove navigation menus, cookie notices, ads, and other website boilerplate
- Format headings, bullet points, and sections appropriately
- Extract and clearly label salary information if present
- Keep the company name and job title prominent
- Output ONLY the Markdown content, no commentary

Raw text:
{raw_text}"""

EXTRACT_SKILLS_PROMPT = """You are a skills extraction expert. Analyze the job posting below and extract all skills mentioned.

Return a JSON object with this exact structure:
{{
  "title": "Job title",
  "company": "Company name",
  "team_division": "Team or division name (or null)",
  "salary_min": null or integer (annual, in the listed currency),
  "salary_max": null or integer (annual, in the listed currency),
  "salary_currency": "USD" (or other currency code),
  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["skill1", "skill2", ...]
}}

Rules:
- Skills should be specific and atomic (e.g., "Python" not "programming languages")
- Separate clearly required skills from preferred/nice-to-have skills
- Include both technical and soft skills
- Normalize skill names (e.g., "React.js" → "React", "Javascript" → "JavaScript")
- If salary is not mentioned, use null for min/max
- Return ONLY valid JSON, no commentary

Job posting:
{job_markdown}"""


class LLMError(Exception):
    """Raised when an LLM API call fails."""


class LLMService:
    """
    Service for interacting with LLM providers.

    Supports OpenAI, Anthropic, and Ollama for:
    - De-noising raw job posting text into Markdown
    - Extracting structured skill data from job postings
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        """
        Initialize the LLM service.

        Args:
            config: LLM configuration (uses defaults if not provided)
        """
        self.config = config or LLMConfig()

    async def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI API.

        Args:
            prompt: The prompt to send

        Returns:
            Response text

        Raises:
            LLMError: If the API call fails
        """
        try:
            from openai import AsyncOpenAI

            api_key = self.config.get_api_key()
            client = AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"OpenAI API call failed: {e}") from e

    async def _call_anthropic(self, prompt: str) -> str:
        """
        Call Anthropic API.

        Args:
            prompt: The prompt to send

        Returns:
            Response text

        Raises:
            LLMError: If the API call fails
        """
        try:
            import anthropic

            api_key = self.config.get_api_key()
            client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            # Find the first text block in the response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text  # type: ignore[union-attr]
            return ""
        except Exception as e:
            raise LLMError(f"Anthropic API call failed: {e}") from e

    async def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama local API.

        Args:
            prompt: The prompt to send

        Returns:
            Response text

        Raises:
            LLMError: If the API call fails
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": self.config.temperature},
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            raise LLMError(f"Ollama API call failed: {e}") from e

    async def complete(self, prompt: str) -> str:
        """
        Send a prompt to the configured LLM provider.

        Args:
            prompt: The prompt to send

        Returns:
            Response text

        Raises:
            LLMError: If the API call fails
            ValueError: If provider is not supported
        """
        provider = self.config.provider

        if provider == "openai":
            return await self._call_openai(prompt)
        elif provider == "anthropic":
            return await self._call_anthropic(prompt)
        elif provider == "ollama":
            return await self._call_ollama(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def denoise_job_posting(self, raw_text: str) -> str:
        """
        Convert raw scraped text into clean Markdown.

        Args:
            raw_text: Raw text extracted from job posting HTML

        Returns:
            Clean Markdown representation of the job posting

        Raises:
            LLMError: If the LLM call fails
        """
        prompt = DENOISE_PROMPT.format(raw_text=raw_text)
        return await self.complete(prompt)

    async def extract_job_data(self, job_markdown: str) -> dict[str, Any]:
        """
        Extract structured job data from Markdown content.

        Args:
            job_markdown: Clean Markdown job posting

        Returns:
            Dictionary with title, company, skills, salary info

        Raises:
            LLMError: If the LLM call fails or response is not valid JSON
        """
        prompt = EXTRACT_SKILLS_PROMPT.format(job_markdown=job_markdown)
        response = await self.complete(prompt)

        # Strip markdown code fences if present
        response = response.strip()
        if response.startswith("```"):
            response = re.sub(r"^```(?:json)?\s*", "", response)
            response = re.sub(r"\s*```$", "", response)

        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM returned invalid JSON: {e}\nResponse: {response}") from e

        # Validate required fields
        required_fields = ["title", "company", "required_skills", "preferred_skills"]
        for field in required_fields:
            if field not in data:
                raise LLMError(f"LLM response missing required field: {field}")

        return data
