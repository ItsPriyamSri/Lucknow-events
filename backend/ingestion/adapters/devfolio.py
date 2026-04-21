"""Devfolio hackathons: Playwright listing → hackathon detail pages."""

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

        # Devfolio listing pages contain relative links like /hackathons/<slug>.
        # Restrict aggressively to hackathon detail pages to avoid crawling site chrome pages.
        def _extract_links(rendered_html: str) -> list[str]:
            pat = re.compile(r'href="([^"]+)"', re.I)
            links = unique_hrefs(rendered_html, base, pat, limit=max_items * 15)
            deny = {"open", "past", "applied"}
            out: list[str] = []
            for u in links:
                if "devfolio.co/hackathons/" not in u:
                    continue
                slug = u.rstrip("/").split("/hackathons/")[-1].split("/")[0].strip()
                if not slug or slug in deny:
                    continue
                # Heuristic: real hackathon slugs are usually short path segments (not tabs like /open).
                if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9-]{2,}", slug):
                    continue
                out.append(u)
            return out

        filtered = _extract_links(html)
        if not filtered:
            # Hackathons listing is heavily client-rendered; retry with Playwright-rendered HTML.
            filtered = _extract_links(await playwright_fetch_html(base, post_load_wait_ms=5000))

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
