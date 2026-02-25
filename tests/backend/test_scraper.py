"""Tests for the web scraping service."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config import ScrapingConfig
from backend.services.scraper import ScraperError, ScraperService, playwright_available


@pytest.fixture
def fast_config():
    """Scraping config with minimal delays for testing."""
    return ScrapingConfig(
        timeout_seconds=5,
        retry_attempts=2,
        user_agent="TestBot/1.0",
        rate_limit_delay_seconds=0,
        min_content_chars=500,
    )


@pytest.fixture
def scraper(fast_config):
    """ScraperService with fast config."""
    return ScraperService(config=fast_config)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rich_html(word_count: int = 200) -> str:
    """Return HTML whose visible text exceeds the default min_content_chars."""
    return "<html><body><p>" + ("word " * word_count) + "</p></body></html>"


def _thin_html() -> str:
    """Return HTML whose visible text is well below min_content_chars."""
    return "<html><body><p>Loading…</p></body></html>"


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

class TestUrlValidation:
    """Tests for URL validation."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert ScraperService.is_valid_url("http://example.com/jobs/123") is True

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert ScraperService.is_valid_url("https://linkedin.com/jobs/123") is True

    def test_valid_greenhouse_url(self):
        """Test valid Greenhouse URL."""
        assert ScraperService.is_valid_url("https://boards.greenhouse.io/company/jobs/123") is True

    def test_invalid_no_scheme(self):
        """Test URL without scheme."""
        assert ScraperService.is_valid_url("example.com/jobs") is False

    def test_invalid_empty(self):
        """Test empty URL."""
        assert ScraperService.is_valid_url("") is False

    def test_invalid_ftp(self):
        """Test FTP URL (not supported)."""
        assert ScraperService.is_valid_url("ftp://example.com/jobs") is False


# ---------------------------------------------------------------------------
# Domain detection
# ---------------------------------------------------------------------------

class TestDomainDetection:
    """Tests for domain detection."""

    def test_get_domain_linkedin(self):
        """Test domain extraction for LinkedIn."""
        domain = ScraperService.get_domain("https://www.linkedin.com/jobs/view/123")
        assert domain == "www.linkedin.com"

    def test_get_domain_indeed(self):
        """Test domain extraction for Indeed."""
        domain = ScraperService.get_domain("https://indeed.com/viewjob?jk=abc")
        assert domain == "indeed.com"

    def test_needs_javascript_linkedin(self, scraper):
        """Test that LinkedIn is flagged as JS-heavy by the domain hint."""
        assert scraper._needs_javascript("https://linkedin.com/jobs/123") is True
        assert scraper._needs_javascript("https://www.linkedin.com/jobs/123") is True

    def test_needs_javascript_greenhouse(self, scraper):
        """Test that Greenhouse does not require JavaScript."""
        assert scraper._needs_javascript("https://boards.greenhouse.io/company/jobs/123") is False

    def test_needs_javascript_lever(self, scraper):
        """Test that Lever does not require JavaScript."""
        assert scraper._needs_javascript("https://jobs.lever.co/company/123") is False

    def test_needs_javascript_indeed(self, scraper):
        """Test that Indeed does not require JavaScript."""
        assert scraper._needs_javascript("https://indeed.com/viewjob?jk=abc") is False


# ---------------------------------------------------------------------------
# Static scraping (httpx)
# ---------------------------------------------------------------------------

class TestStaticScraping:
    """Tests for static site scraping with httpx."""

    @pytest.mark.asyncio
    async def test_scrape_successful(self, scraper):
        """Test successful scraping of a static page via _scrape_with_httpx."""
        mock_html = "<html><body><h1>Software Engineer</h1></body></html>"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await scraper._scrape_with_httpx("https://greenhouse.io/jobs/123")
            assert result == mock_html

    @pytest.mark.asyncio
    async def test_scrape_raises_on_invalid_url(self, scraper):
        """Test that invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL"):
            await scraper.scrape("not-a-valid-url")

    @pytest.mark.asyncio
    async def test_scrape_retries_on_error(self, scraper):
        """Test that scraper retries on connection error."""
        import httpx as httpx_module

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx_module.RequestError("Connection failed")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(ScraperError):
                await scraper._scrape_with_httpx("https://greenhouse.io/jobs/123")

            assert mock_client.get.call_count == scraper.config.retry_attempts


# ---------------------------------------------------------------------------
# scrape() routing logic
# ---------------------------------------------------------------------------

class TestScrapeMethod:
    """Tests for the main scrape() routing / decision logic."""

    @pytest.mark.asyncio
    async def test_linkedin_com_raises_unsupported(self, scraper):
        """linkedin.com URLs raise ScraperError immediately."""
        with pytest.raises(ScraperError, match="not supported"):
            await scraper.scrape("https://linkedin.com/jobs/123")

    @pytest.mark.asyncio
    async def test_www_linkedin_raises_unsupported(self, scraper):
        """www.linkedin.com URLs raise ScraperError immediately."""
        with pytest.raises(ScraperError, match="not supported"):
            await scraper.scrape("https://www.linkedin.com/jobs/view/99999")

    @pytest.mark.asyncio
    async def test_rich_static_content_skips_playwright(self, scraper):
        """When httpx returns rich content, playwright_available is never consulted."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = _rich_html()
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            pw_check = MagicMock()
            with patch("backend.services.scraper.playwright_available", pw_check):
                result = await scraper.scrape("https://boards.greenhouse.io/jobs/123")

        assert result == _rich_html()
        pw_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_thin_content_raises_when_playwright_unavailable(self, scraper):
        """Thin httpx content + Playwright not installed → ScraperError with install tip."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = _thin_html()
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("backend.services.scraper.playwright_available", return_value=False):
                with pytest.raises(ScraperError, match="Playwright is not installed"):
                    await scraper.scrape("https://boards.greenhouse.io/jobs/123")

    @pytest.mark.asyncio
    async def test_thin_content_falls_back_to_playwright(self, scraper):
        """Thin httpx content + Playwright available → _scrape_with_playwright called."""
        playwright_html = _rich_html(300)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.text = _thin_html()
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("backend.services.scraper.playwright_available", return_value=True):
                with patch.object(
                    scraper, "_scrape_with_playwright", new=AsyncMock(return_value=playwright_html)
                ) as mock_pw:
                    result = await scraper.scrape("https://some-js-site.com/jobs/123")

        assert result == playwright_html
        mock_pw.assert_called_once_with("https://some-js-site.com/jobs/123")

    @pytest.mark.asyncio
    async def test_httpx_error_falls_through_to_playwright(self, scraper):
        """ScraperError from httpx falls through to Playwright when available."""
        playwright_html = _rich_html(300)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            import httpx as _httpx

            mock_client.get = AsyncMock(side_effect=_httpx.RequestError("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("backend.services.scraper.playwright_available", return_value=True):
                with patch.object(
                    scraper, "_scrape_with_playwright", new=AsyncMock(return_value=playwright_html)
                ) as mock_pw:
                    result = await scraper.scrape("https://some-js-site.com/jobs/123")

        assert result == playwright_html
        mock_pw.assert_called_once()

    @pytest.mark.asyncio
    async def test_httpx_error_raises_when_playwright_unavailable(self, scraper):
        """ScraperError from httpx + no Playwright → ScraperError with install tip."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            import httpx as _httpx

            mock_client.get = AsyncMock(side_effect=_httpx.RequestError("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("backend.services.scraper.playwright_available", return_value=False):
                with pytest.raises(ScraperError, match="Playwright is not installed"):
                    await scraper.scrape("https://some-js-site.com/jobs/123")


# ---------------------------------------------------------------------------
# playwright_available() helper
# ---------------------------------------------------------------------------

class TestPlaywrightAvailability:
    """Tests for the playwright_available() module-level helper."""

    def test_playwright_not_available_when_missing(self):
        """Returns False when sys.modules blocks the playwright import."""
        with patch.dict(sys.modules, {"playwright": None}):
            assert playwright_available() is False

    def test_playwright_available_returns_bool(self):
        """Returns a plain bool regardless of installation state."""
        result = playwright_available()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# HTML text extraction
# ---------------------------------------------------------------------------

class TestHtmlExtraction:
    """Tests for HTML text extraction."""

    def test_extract_basic_text(self):
        """Test basic text extraction from HTML."""
        html = "<html><body><h1>Job Title</h1><p>Job description here.</p></body></html>"
        text = ScraperService.extract_text_from_html(html)
        assert "Job Title" in text
        assert "Job description here." in text

    def test_extract_removes_scripts(self):
        """Test that script tags are removed."""
        html = "<html><body><p>Real content</p><script>var x = 1;</script></body></html>"
        text = ScraperService.extract_text_from_html(html)
        assert "Real content" in text
        assert "var x = 1" not in text

    def test_extract_removes_styles(self):
        """Test that style tags are removed."""
        html = "<html><body><p>Content</p><style>.class { color: red; }</style></body></html>"
        text = ScraperService.extract_text_from_html(html)
        assert "Content" in text
        assert "color: red" not in text

    def test_extract_removes_nav(self):
        """Test that navigation is removed."""
        html = "<html><body><nav>Menu items</nav><main><p>Job content</p></main></body></html>"
        text = ScraperService.extract_text_from_html(html)
        assert "Job content" in text
        assert "Menu items" not in text

    def test_extract_whitespace_normalization(self):
        """Test that excessive whitespace is normalized."""
        html = "<html><body><p>Line  1</p>\n\n\n<p>Line 2</p></body></html>"
        text = ScraperService.extract_text_from_html(html)
        # Should not have excessive blank lines
        assert "\n\n\n" not in text

    def test_extract_empty_html(self):
        """Test extraction from empty-ish HTML."""
        html = "<html><body></body></html>"
        text = ScraperService.extract_text_from_html(html)
        assert text == ""
