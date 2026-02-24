"""Tests for the web scraping service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config import ScrapingConfig
from backend.services.scraper import ScraperError, ScraperService


@pytest.fixture
def fast_config():
    """Scraping config with minimal delays for testing."""
    return ScrapingConfig(
        timeout_seconds=5,
        retry_attempts=2,
        user_agent="TestBot/1.0",
        rate_limit_delay_seconds=0,
    )


@pytest.fixture
def scraper(fast_config):
    """ScraperService with fast config."""
    return ScraperService(config=fast_config)


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
        """Test that LinkedIn requires JavaScript."""
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


class TestStaticScraping:
    """Tests for static site scraping with httpx."""

    @pytest.mark.asyncio
    async def test_scrape_successful(self, scraper):
        """Test successful scraping of a static page."""
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
