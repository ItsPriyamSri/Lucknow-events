from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import structlog

from ingestion.adapters.base import BaseAdapter, ScrapedPage
from ingestion.normalizers.text import MAX_EXTRACTION_CHARS, clean_text


log = structlog.get_logger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 LucknowTechEventsBot/0.1"
)


class GenericAdapter(BaseAdapter):
    """
    Fallback for any URL-based source.
    Uses Playwright to render the page, extracts visible text, and
    routes it through the AI Extraction Agent (primary method).
    """

    platform = "generic"
    crawl_strategy = "playwright"

    async def fetch(self, source: dict[str, Any]) -> list[ScrapedPage]:
        url = source.get("base_url", "")
        if not url:
            raise ValueError("Generic source has no base_url")

        html = await _playwright_render(url)
        return [
            ScrapedPage(
                url=url,
                html_or_json=html,
                fetched_at=datetime.now(timezone.utc),
                status_code=200,
                page_type="detail",
            )
        ]

    def extract_raw_events(self, page: ScrapedPage) -> list[dict[str, Any]]:
        """
        For the generic adapter the AI extraction agent is the primary parser,
        so we return the cleaned text as a single raw event payload.
        """
        text = clean_text(str(page.html_or_json), max_chars=MAX_EXTRACTION_CHARS)
        return [{"_cleaned_text": text, "canonical_url": page.url}]

    def get_external_id(self, raw: dict[str, Any]) -> str | None:
        return None


async def _playwright_render(url: str) -> str:
    """
    Render the page with Playwright (async), return visible page text.
    Falls back to httpx if Playwright is unavailable (e.g. no browser installed).
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context(user_agent=_USER_AGENT)
            page = await ctx.new_page()
            import asyncio
            await asyncio.sleep(random.uniform(0.5, 2.0))
            try:
                await page.goto(url, wait_until="networkidle", timeout=30_000)
            except Exception:
                await page.goto(url, timeout=30_000)
            content = await page.inner_text("body")
            await browser.close()
            return content
    except Exception as exc:
        log.warning("generic.playwright_failed", url=url, error=str(exc))
        return await _httpx_fallback(url)


async def _httpx_fallback(url: str) -> str:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": _USER_AGENT}) as client:
            r = await client.get(url, follow_redirects=True)
            return r.text
    except Exception as exc:
        log.error("generic.httpx_fallback_failed", url=url, error=str(exc))
        return ""
