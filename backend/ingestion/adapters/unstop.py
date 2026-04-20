"""Unstop: internal listing API with Playwright fallback."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from ingestion.adapters.base import BaseAdapter, ScrapedPage
from ingestion.adapters.playwright_util import USER_AGENT, playwright_render

log = structlog.get_logger(__name__)


class UnstopAdapter(BaseAdapter):
    platform = "unstop"
    crawl_strategy = "api_then_playwright"

    async def fetch(self, source: dict[str, Any]) -> list[ScrapedPage]:
        cfg = source.get("config_json") or {}
        location = cfg.get("location", "Lucknow")
        max_items = int(cfg.get("max_items", 20))

        api_url = f"https://unstop.com/api/opportunity/listing?location={location}&per_page={max_items}"
        pages: list[ScrapedPage] = []
        now = datetime.now(timezone.utc)

        try:
            async with httpx.AsyncClient(timeout=45, headers={"User-Agent": USER_AGENT}) as client:
                r = await client.get(api_url, follow_redirects=True)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            log.warning("unstop.api_failed", error=str(exc))
            data = None

        if isinstance(data, dict):
            rows = data.get("data") or data.get("opportunities") or data.get("results") or data.get("list") or []
            if isinstance(rows, dict):
                rows = rows.get("data") or rows.get("records") or []
            if isinstance(rows, list):
                for row in rows[:max_items]:
                    if not isinstance(row, dict):
                        continue
                    title = row.get("title") or row.get("name") or row.get("heading")
                    link = row.get("seo_url") or row.get("url") or row.get("public_url") or row.get("slug")
                    if not title:
                        continue
                    if link and not str(link).startswith("http"):
                        link = "https://unstop.com/" + str(link).lstrip("/")
                    canonical = link or source.get("base_url", "")
                    start = row.get("start_date") or row.get("starts_at") or row.get("registration_start_date")
                    end = row.get("end_date") or row.get("ends_at")
                    venue = row.get("venue") or row.get("location")
                    raw = {
                        "title": str(title),
                        "canonical_url": canonical,
                        "start_at": str(start) if start else None,
                        "end_at": str(end) if end else None,
                        "venue_name": str(venue) if venue else None,
                        "description": row.get("description") or row.get("short_description"),
                        "poster_url": row.get("logoUrl2") or row.get("image") or row.get("banner"),
                        "city": location,
                    }
                    pages.append(
                        ScrapedPage(
                            url=canonical,
                            html_or_json=json.dumps(raw, ensure_ascii=False),
                            fetched_at=now,
                            status_code=200,
                            page_type="api_response",
                        )
                    )

        if pages:
            return pages

        # Fallback: render competitions listing and extract card links
        base = source.get("base_url") or "https://unstop.com/competitions"
        html = await playwright_render(base)
        href_re = re.compile(r'href="([^"]*unstop\.com/[^"]+)"', re.I)
        seen: set[str] = set()
        links: list[str] = []
        for m in href_re.finditer(html):
            u = m.group(1).split("#")[0]
            if "/competitions/" in u or "/hackathons/" in u or "/events/" in u:
                if u.startswith("/"):
                    u = "https://unstop.com" + u
                if u not in seen:
                    seen.add(u)
                    links.append(u)
            if len(links) >= max_items:
                break

        for link in links:
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
        return pages

    def extract_raw_events(self, page: ScrapedPage) -> list[dict[str, Any]]:
        if page.page_type == "api_response":
            try:
                d = json.loads(str(page.html_or_json))
                return [d]
            except Exception:
                pass
        from ingestion.normalizers.text import MAX_EXTRACTION_CHARS, clean_text

        text = clean_text(str(page.html_or_json), max_chars=MAX_EXTRACTION_CHARS)
        return [{"_cleaned_text": text, "canonical_url": page.url}]

    def get_external_id(self, raw: dict[str, Any]) -> str | None:
        u = raw.get("canonical_url") or raw.get("url")
        if u:
            return str(u).split("/")[-1][:200] or None
        return None
