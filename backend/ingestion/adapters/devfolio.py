"""Devfolio hackathons: Playwright listing → hackathon detail pages."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import structlog

from ingestion.adapters.base import BaseAdapter, ScrapedPage
from ingestion.adapters.playwright_util import httpx_fetch_text, playwright_render, unique_hrefs

log = structlog.get_logger(__name__)


class DevfolioAdapter(BaseAdapter):
    platform = "devfolio"
    crawl_strategy = "playwright"

    async def fetch(self, source: dict[str, Any]) -> list[ScrapedPage]:
        base = source.get("base_url", "https://devfolio.co/hackathons").rstrip("/")
        cfg = source.get("config_json") or {}
        max_items = int(cfg.get("max_items", 12))
        location_hint = (cfg.get("location_filter") or "lucknow").lower()
        now = datetime.now(timezone.utc)

        html = await httpx_fetch_text(base)
        if len(html) < 500:
            html = await playwright_render(base)

        pat = re.compile(r'href="(https://[^"]*devfolio\.co/[^"?#]+)"', re.I)
        links = unique_hrefs(html, base, pat, limit=max_items * 3)
        # Prefer hackathon / event paths
        filtered = [
            u
            for u in links
            if "/hackathons/" in u or "/events/" in u or "/hackathon/" in u
        ]
        if not filtered:
            filtered = links

        # Optional crude location filter using page text later; here filter URL/query if present
        if location_hint:
            narrowed = [u for u in filtered if location_hint in u.lower()]
            if narrowed:
                filtered = narrowed

        pages: list[ScrapedPage] = []
        for link in filtered[:max_items]:
            body = await playwright_render(link)
            pages.append(
                ScrapedPage(
                    url=link,
                    html_or_json=body,
                    fetched_at=now,
                    status_code=200,
                    page_type="detail",
                )
            )
        if not pages:
            log.warning("devfolio.no_links", base=base)
        return pages

    def extract_raw_events(self, page: ScrapedPage) -> list[dict[str, Any]]:
        from ingestion.normalizers.text import MAX_EXTRACTION_CHARS, clean_text

        text = clean_text(str(page.html_or_json), max_chars=MAX_EXTRACTION_CHARS)
        return [{"_cleaned_text": text, "canonical_url": page.url}]

    def get_external_id(self, raw: dict[str, Any]) -> str | None:
        u = raw.get("canonical_url")
        if u:
            return str(u).rstrip("/").split("/")[-1][:200]
        return None
