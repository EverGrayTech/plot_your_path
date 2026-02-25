# Plan: Scraper Resilience — Decouple CLI from Playwright

## Problem Statement

Running `capture.py` in a WSL (or any headless Linux) environment fails because Playwright
requires a separately-installed Chromium binary (`playwright install chromium`) and a full
X11/system-library stack that is typically absent in WSL. The current design makes Playwright
a **hard, always-imported core dependency**, even though the vast majority of target URLs
(Greenhouse, Lever, Workday, most direct ATS links) are fully static and never need a browser.

The only site that currently triggers Playwright is `linkedin.com` — and LinkedIn is
notoriously hostile to all scrapers (including Playwright), because it walls off job listings
behind authentication.

**Bottom line:** The CLI does not need to be tied to a browser for any realistic use case.

---

## Root Causes

| # | Root Cause | Impact |
|---|-----------|--------|
| 1 | `playwright` is a hard core dependency in `pyproject.toml` | Must be installed (and `playwright install` run) just to `import` the scraper module |
| 2 | `from playwright.async_api import ...` is a top-level import in `scraper.py` | Fails at import time if Playwright is not installed — crashes before any URL is even tested |
| 3 | `JS_REQUIRED_DOMAINS` hard-routes LinkedIn to Playwright | Even if Playwright is installed, LinkedIn requires auth and blocks headless browsers |
| 4 | No httpx-first fallback for JS-tagged domains | Forces browser path even when a simple GET would return enough content |

---

## Goals

| # | Goal | Outcome |
|---|------|---------|
| 1 | Make Playwright an optional extra | `uv sync` (default) installs zero browser dependency |
| 2 | Make the Playwright import lazy | Importing `scraper.py` never crashes even if Playwright is absent |
| 3 | Add `httpx`-first fallback for JS-tagged domains | Try static scrape first; only attempt Playwright if content is too thin |
| 4 | Give clear, actionable errors for LinkedIn | Tell the user exactly why LinkedIn is unsupported and what to try instead |
| 5 | Keep all existing tests green, add new coverage for fallback paths | ≥90% line coverage maintained |

---

## Architecture Design

### Scraping Decision Tree (new)

```
capture.py receives URL
        │
        ▼
is_valid_url()?  ──No──▶ ValueError
        │ Yes
        ▼
domain in UNSUPPORTED_DOMAINS (linkedin)?
        │ Yes
        ▼
raise ScraperError("LinkedIn requires auth; use the direct ATS link instead")
        │
        │ No
        ▼
Try _scrape_with_httpx()
        │
        ├── Success + content rich enough?  ──Yes──▶ return HTML
        │
        └── Thin content OR failed?
                │
                ▼
        playwright_available()?  ──No──▶ raise ScraperError(clear install instructions)
                │ Yes
                ▼
        _scrape_with_playwright()  ──▶ return HTML
```

**"Content rich enough"** = `len(extracted_text) > MIN_CONTENT_CHARS` (configurable, default
`500`).  This avoids false positives from sites that return a minimal "please enable JS" shell.

### `playwright_available()` helper

```python
def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False
```

Lazy-checked at call time — never at module import time.

---

## Affected Files

| File | Change Type | Change |
|------|-------------|--------|
| `pyproject.toml` | Modify | Move `playwright` to `[project.optional-dependencies]` under new `browser` extra |
| `src/backend/services/scraper.py` | Modify | Lazy Playwright import, add `UNSUPPORTED_DOMAINS`, `MIN_CONTENT_CHARS`, httpx-first fallback, `playwright_available()` |
| `config/scraping.json` | Modify | Add `min_content_chars: 500` |
| `src/backend/config.py` | Modify | Add `min_content_chars: int = 500` to `ScrapingConfig` |
| `tests/backend/test_scraper.py` | Modify | Add tests for: LinkedIn UNSUPPORTED error, thin-content fallback path, `playwright_available()` helper |

---

## Implementation Steps

### Step 1 — Update `pyproject.toml`

Move `playwright>=1.48.0` from `dependencies` to a new optional extra:

```toml
[project.optional-dependencies]
browser = ["playwright>=1.48.0"]
dev = [...]
```

Install with: `uv sync --extra browser && uv run playwright install chromium`
Default install (`uv sync`) remains browser-free.

### Step 2 — Update `config/scraping.json` + `ScrapingConfig`

Add `min_content_chars` (threshold below which we consider a static scrape "too thin"):

```json
{
  "timeout_seconds": 30,
  "retry_attempts": 3,
  "user_agent": "Mozilla/5.0 (compatible; PlotYourPath/1.0)",
  "rate_limit_delay_seconds": 2,
  "min_content_chars": 500
}
```

Add `min_content_chars: int = 500` to `ScrapingConfig`.

### Step 3 — Refactor `scraper.py`

1. **Remove** the top-level `from playwright.async_api import Page, async_playwright` import.
2. **Add** `UNSUPPORTED_DOMAINS` (LinkedIn) and `MIN_CONTENT_CHARS` constants.
3. **Add** `playwright_available()` module-level helper that lazy-imports.
4. **Update** `_needs_javascript()` → `_prefers_javascript()` or keep name but change semantics.
5. **Update** `_scrape_with_playwright()` to do a lazy import of `async_playwright` inside the method body, with a clear `ImportError` → `ScraperError` conversion.
6. **Update** `scrape()` to implement the new decision tree above.

Key snippet for `scrape()`:

```python
async def scrape(self, url: str) -> str:
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

    # Always try httpx first — it works for most ATS platforms
    try:
        html = await self._scrape_with_httpx(url)
        text = self.extract_text_from_html(html)
        if len(text) >= self.config.min_content_chars:
            return html
        # Content too thin — site likely needs JS rendering
    except ScraperError:
        html = ""  # Fall through to Playwright

    if not self._scrape_with_playwright_available():
        raise ScraperError(
            "Scraped content was too thin (JavaScript rendering required) and "
            "Playwright is not installed. Install it with:\n"
            "  uv sync --extra browser\n"
            "  uv run playwright install chromium"
        )

    return await self._scrape_with_playwright(url)
```

### Step 4 — Update `_scrape_with_playwright()`

Move the `async_playwright` import inside the method:

```python
async def _scrape_with_playwright(self, url: str) -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise ScraperError(
            "Playwright is not installed. Run: uv sync --extra browser && "
            "uv run playwright install chromium"
        ) from e
    # ... rest unchanged ...
```

### Step 5 — Update tests

- Update `test_needs_javascript_linkedin` → `test_linkedin_raises_unsupported` (scraping a LinkedIn URL should now raise `ScraperError`, not try Playwright)
- Add `test_thin_content_falls_back_to_playwright_when_available`
- Add `test_thin_content_raises_when_playwright_unavailable`
- Add `test_playwright_available_when_installed` / `test_playwright_available_when_missing`

### Step 6 — Commit

```
fix(scraper): decouple CLI from Playwright; make browser an optional extra

Playwright is moved to an optional [browser] dependency group. The scraper
now uses httpx-first for all URLs, falling back to Playwright only when
content is too thin. LinkedIn is explicitly unsupported with a clear error
message pointing users to the direct ATS link.
```

---

## Out of Scope

- LinkedIn authentication / cookie-based scraping
- Indeed support (also blocks headless scrapers)
- Any frontend changes
- Playwright-based tests in CI (requires browser install)

---

## Success Criteria

- [ ] `uv sync` (no extras) completes with zero Playwright-related output
- [ ] `uv run python capture.py <greenhouse-or-lever-url>` works in WSL without any browser installed
- [ ] `uv run python capture.py <linkedin-url>` prints a clear, human-readable error with actionable instructions
- [ ] All existing tests pass; new tests cover the fallback and LinkedIn-rejection paths
- [ ] ≥90% line coverage maintained
