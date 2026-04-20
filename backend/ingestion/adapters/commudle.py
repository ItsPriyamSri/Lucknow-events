"""Commudle: Playwright on community events listing → detail pages (AI extraction)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import structlog

from ingestion.adapters.base import BaseAdapter, ScrapedPage
from ingestion.adapters.playwright_util import httpx_fetch_text, playwright_render, unique_hrefs

log = structlog.get_logger(__name__)


class CommudleAdapter(BaseAdapter):
    platform = "commudle"
    crawl_strategy = "playwright"

    async def fetch(self, source: dict[str, Any]) -> list[ScrapedPage]:
        base = source.get("base_url", "").rstrip("/")
        cfg = source.get("config_json") or {}
        max_items = int(cfg.get("max_items", 12))
        now = datetime.now(timezone.utc)

        html = await httpx_fetch_text(base)
        if len(html) < 500:
            html = await playwright_render(base)

        # Event detail URLs on commudle
        pat = re.compile(r'href="(https://www\.commudle\.com/events/[^"?#]+)"', re.I)
        links = unique_hrefs(html, base, pat, limit=max_items)
        if not links:
            # Broader match
            pat2 = re.compile(r'href="(/events/[^"?#]+)"', re.I)
            for m in pat2.finditer(html):
                u = "https://www.commudle.com" + m.group(1)
                if u not in links:
                    links.append(u)
                if len(links) >= max_items:
                    break

        pages: list[ScrapedPage] = []
        for link in links[:max_items]:
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
            log.warning("commudle.no_links", base=base)
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
