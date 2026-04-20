from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ingestion.adapters.base import BaseAdapter, ScrapedPage
from ingestion.adapters.playwright_util import playwright_render
from ingestion.normalizers.text import MAX_EXTRACTION_CHARS, clean_text


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

        html = await playwright_render(url)
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
