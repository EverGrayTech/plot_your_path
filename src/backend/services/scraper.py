"""Web scraping service for job postings."""

import asyncio
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from backend.config import ScrapingConfig


def playwright_available() -> bool:
    """
    Check whether the optional Playwright package is importable.

    Returns:
        True if Playwright is installed, False otherwise.
    """
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


class ScraperError(Exception):
    """Raised when scraping fails."""


class ScraperService:
    """
    Service for scraping job posting HTML from various job sites.

    Scraping strategy:
    - Explicitly unsupported domains (e.g. LinkedIn) raise immediately with
      a helpful error pointing users to the direct ATS link.
    - All other URLs are attempted first with httpx (works for most ATS
      platforms: Greenhouse, Lever, Workday, etc.).
    - If the returned content is too thin (JavaScript-rendered gating page),
      the scraper falls back to Playwright if it is installed; otherwise it
      raises a clear error explaining how to install the optional extra.
    """

    # Sites that are explicitly not supported (require auth / block scrapers)
    UNSUPPORTED_DOMAINS: frozenset[str] = frozenset({"linkedin.com", "www.linkedin.com"})

    # Sites known to need JavaScript for meaningful content (used as a hint,
    # not a hard gate — the thin-content fallback handles this automatically)
    JS_REQUIRED_DOMAINS: frozenset[str] = frozenset({"linkedin.com", "www.linkedin.com"})

    def __init__(self, config: ScrapingConfig | None = None) -> None:
        """
        Initialize the scraper service.

        Args:
            config: Scraping configuration (uses defaults if not provided)
        """
        self.config = config or ScrapingConfig()

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

    def _needs_javascript(self, url: str) -> bool:
        """
        Hint whether a URL typically requires JavaScript rendering.

        Note: this is a domain-level hint only.  The main ``scrape()`` method
        always attempts httpx first, regardless of this flag, and uses actual
        content length to decide whether Playwright is needed.

        Args:
            url: URL to check

        Returns:
            True if the domain is known to be JS-heavy
        """
        return self.get_domain(url) in self.JS_REQUIRED_DOMAINS

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

        Playwright is an optional dependency (``uv sync --extra browser``).
        This method lazy-imports it and raises ``ScraperError`` with install
        instructions if the package is absent.

        Args:
            url: URL to scrape

        Returns:
            Raw HTML content

        Raises:
            ScraperError: If Playwright is not installed or scraping fails
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise ScraperError(
                "Playwright is not installed. Run:\n"
                "  uv sync --extra browser\n"
                "  uv run playwright install chromium"
            ) from e

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

        Decision flow:
        1. Validate URL — raise ValueError for malformed input.
        2. Reject explicitly unsupported domains (LinkedIn) with a clear error.
        3. Try httpx first — works for Greenhouse, Lever, Workday, and most ATS.
        4. If content is too thin (JS gating page), fall back to Playwright.
           If Playwright is not installed, raise ScraperError with install steps.

        Args:
            url: Job posting URL to scrape

        Returns:
            Raw HTML content

        Raises:
            ValueError: If URL is invalid
            ScraperError: If the domain is unsupported or scraping fails
        """
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        domain = self.get_domain(url)

        if domain in self.UNSUPPORTED_DOMAINS:
            raise ScraperError(
                f"'{domain}' is not supported: LinkedIn requires authentication and "
                "actively blocks automated access. Use the direct ATS link "
                "(Greenhouse, Lever, Workday, etc.) listed in the job posting instead."
            )

        await asyncio.sleep(self.config.rate_limit_delay_seconds)

        # Always try httpx first — works for most ATS platforms without a browser
        html = ""
        try:
            html = await self._scrape_with_httpx(url)
            text = self.extract_text_from_html(html)
            if len(text) >= self.config.min_content_chars:
                return html
            # Content below threshold — site is likely gating behind JavaScript
        except ScraperError:
            pass  # Fall through to Playwright

        if not playwright_available():
            raise ScraperError(
                "Scraped content was too thin (JavaScript rendering likely required) and "
                "Playwright is not installed. Install it with:\n"
                "  uv sync --extra browser\n"
                "  uv run playwright install chromium"
            )

        return await self._scrape_with_playwright(url)

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
