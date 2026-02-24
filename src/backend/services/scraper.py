"""Web scraping service for job postings."""

import asyncio
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright

from backend.config import ScrapingConfig


class ScraperError(Exception):
    """Raised when scraping fails."""


class ScraperService:
    """
    Service for scraping job posting HTML from various job sites.

    Supports both static (httpx + BeautifulSoup) and JavaScript-heavy
    (Playwright) scraping strategies.
    """

    # Sites that require JavaScript rendering
    JS_REQUIRED_DOMAINS = {"linkedin.com", "www.linkedin.com"}

    def __init__(self, config: ScrapingConfig | None = None) -> None:
        """
        Initialize the scraper service.

        Args:
            config: Scraping configuration (uses defaults if not provided)
        """
        self.config = config or ScrapingConfig()

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Validate if a URL is properly formatted.

        Args:
            url: URL string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except ValueError:
            return False

    @staticmethod
    def get_domain(url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: URL string

        Returns:
            Domain string (e.g. 'linkedin.com')
        """
        return urlparse(url).netloc.lower()

    def _needs_javascript(self, url: str) -> bool:
        """
        Check if URL requires JavaScript rendering.

        Args:
            url: URL to check

        Returns:
            True if JavaScript is required
        """
        domain = self.get_domain(url)
        return domain in self.JS_REQUIRED_DOMAINS

    async def _scrape_with_httpx(self, url: str) -> str:
        """
        Scrape HTML using httpx (for static sites).

        Args:
            url: URL to scrape

        Returns:
            Raw HTML content

        Raises:
            ScraperError: If scraping fails after retries
        """
        headers = {"User-Agent": self.config.user_agent}
        last_error: Exception | None = None

        for attempt in range(self.config.retry_attempts):
            try:
                async with httpx.AsyncClient(
                    timeout=self.config.timeout_seconds, follow_redirects=True
                ) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = self.config.rate_limit_delay_seconds * (2**attempt)
                    await asyncio.sleep(wait_time)
                last_error = e
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.rate_limit_delay_seconds)

        raise ScraperError(
            f"Failed to scrape {url} after {self.config.retry_attempts} attempts: {last_error}"
        )

    async def _scrape_with_playwright(self, url: str) -> str:
        """
        Scrape HTML using Playwright (for JavaScript-heavy sites).

        Args:
            url: URL to scrape

        Returns:
            Raw HTML content

        Raises:
            ScraperError: If scraping fails
        """
        last_error: Exception | None = None

        for attempt in range(self.config.retry_attempts):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    try:
                        page = await browser.new_page()
                        await page.set_extra_http_headers(
                            {"User-Agent": self.config.user_agent}
                        )
                        await page.goto(
                            url,
                            timeout=self.config.timeout_seconds * 1000,
                            wait_until="networkidle",
                        )
                        # Wait for job content to load
                        await page.wait_for_timeout(2000)
                        html = await page.content()
                        return html
                    finally:
                        await browser.close()
            except Exception as e:
                last_error = e
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.rate_limit_delay_seconds)

        raise ScraperError(
            f"Failed to scrape {url} with Playwright after {self.config.retry_attempts} "
            f"attempts: {last_error}"
        )

    async def scrape(self, url: str) -> str:
        """
        Scrape job posting HTML from URL.

        Automatically selects the appropriate scraping strategy based on the URL.

        Args:
            url: Job posting URL to scrape

        Returns:
            Raw HTML content

        Raises:
            ValueError: If URL is invalid
            ScraperError: If scraping fails
        """
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        # Add rate limiting delay
        await asyncio.sleep(self.config.rate_limit_delay_seconds)

        if self._needs_javascript(url):
            return await self._scrape_with_playwright(url)
        else:
            return await self._scrape_with_httpx(url)

    @staticmethod
    def extract_text_from_html(html: str) -> str:
        """
        Extract clean text from HTML, removing scripts and styles.

        Args:
            html: Raw HTML content

        Returns:
            Cleaned text content
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style tags
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        # Get text with whitespace normalization
        text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
