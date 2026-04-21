"""Commudle: Playwright on community events listing → detail pages (AI extraction)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import structlog

from ingestion.adapters.base import BaseAdapter, ScrapedPage
from ingestion.adapters.playwright_util import (
    httpx_fetch_text,
    playwright_fetch_html,
    playwright_render,
    unique_hrefs,
)

log = structlog.get_logger(__name__)


class CommudleAdapter(BaseAdapter):
    platform = "commudle"
    crawl_strategy = "playwright"

    async def fetch(self, source: dict[str, Any]) -> list[ScrapedPage]:
        base = source.get("base_url", "").rstrip("/")
        cfg = source.get("config_json") or {}
        max_items = int(cfg.get("max_items", 12))
        now = datetime.now(timezone.utc)

        # Commudle is JS-heavy; href discovery needs rendered HTML (not inner_text).
        html = await httpx_fetch_text(base)
        if len(html) < 500:
            html = await playwright_fetch_html(base, post_load_wait_ms=4000)

        # Event detail URLs on Commudle commonly look like:
        # - https://www.commudle.com/events/<slug>
        # - https://www.commudle.com/communities/<slug>/events/<slug>
        # - https://www.commudle.com/communities/<slug>/hackathons/<slug>
        pat = re.compile(
            r'href="('
            r'https://www\.commudle\.com/(?:events|communities/[^/]+/(?:events|hackathons))/[^"?#]+'
            r'|/(?:events|communities/[^/]+/(?:events|hackathons))/[^"?#]+'
            r')"',
            re.I,
        )
        links = unique_hrefs(html, base, pat, limit=max_items * 3)

        # Normalize relative → absolute; keep only commudle event-ish URLs.
        normalized: list[str] = []
        seen: set[str] = set()
        for u in links:
            if u.startswith("/"):
                u = "https://www.commudle.com" + u
            u = u.split("?")[0].rstrip("/")
            if "commudle.com/" not in u:
                continue
            if u in seen:
                continue
            seen.add(u)
            normalized.append(u)

        pages: list[ScrapedPage] = []
        for link in normalized[:max_items]:
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
