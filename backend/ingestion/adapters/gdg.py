from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from ingestion.adapters.base import BaseAdapter, ScrapedPage


log = structlog.get_logger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 LucknowTechEventsBot/0.1"
)


class GDGAdapter(BaseAdapter):
    platform = "gdg"
    crawl_strategy = "json_feed"

    async def fetch(self, source: dict[str, Any]) -> list[ScrapedPage]:
        """
        Resilient strategy:
          1. Try the publicly visible v0/events endpoint for the chapter.
          2. If that yields no results or fails, fall back to the chapter's
             event listing page via httpx (lightweight HTML; no Playwright needed
             because the chapter page typically exposes JSON-LD / og tags).
        """
        chapter_slug = (source.get("config_json") or {}).get("chapter_slug", "")
        if not chapter_slug:
            raise ValueError("GDG source missing config_json.chapter_slug")

        pages: list[ScrapedPage] = []

        cfg = source.get("config_json") or {}
        max_items = int(cfg.get("max_items", 12))

        # NOTE: gdg.community.dev has started returning 403 to unauthenticated API calls.
        # So we crawl the publicly-rendered chapter page, extract event detail links,
        # then fetch each detail page (which is stable and contains structured text).

        chapter_url = source.get("base_url", f"https://gdg.community.dev/{chapter_slug}/")
        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
            ) as client:
                await _jitter()
                r = await client.get(chapter_url)
                listing_html = r.text
        except Exception as exc:
            log.error("gdg.chapter_fetch_failed", error=str(exc), url=chapter_url)
            return []

        # Extract event detail URLs from listing HTML.
        # Example: https://gdg.community.dev/events/details/google-gdg-lucknow-presents-...
        href_pat = (
            r'href="(https://gdg\.community\.dev/events/details/[^"#?]+)"'
        )
        detail_urls = list(dict.fromkeys(re.findall(href_pat, listing_html, flags=re.I)))

        if not detail_urls:
            # Fallback: still return the chapter page so the pipeline can try AI extraction.
            pages.append(
                ScrapedPage(
                    url=chapter_url,
                    html_or_json=listing_html,
                    fetched_at=datetime.now(timezone.utc),
                    status_code=200,
                    page_type="listing",
                )
            )
            return pages

        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        ) as client:
            for url in detail_urls[:max_items]:
                try:
                    await _jitter()
                    rr = await client.get(url)
                    pages.append(
                        ScrapedPage(
                            url=url,
                            html_or_json=rr.text,
                            fetched_at=datetime.now(timezone.utc),
                            status_code=rr.status_code,
                            page_type="detail",
                        )
                    )
                except Exception as exc:
                    log.warning("gdg.event_fetch_failed", url=url, error=str(exc))

        return pages

    def extract_raw_events(self, page: ScrapedPage) -> list[dict[str, Any]]:
        # We currently rely on AI extraction for HTML pages (listing or detail).
        # Provide cleaned text to the AI layer.
        from ingestion.normalizers.text import MAX_EXTRACTION_CHARS, clean_text

        text = clean_text(str(page.html_or_json), max_chars=MAX_EXTRACTION_CHARS)
        return [{"_cleaned_text": text, "canonical_url": page.url}]

    def _parse_api_response(self, page: ScrapedPage) -> list[dict[str, Any]]:
        data = page.html_or_json
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return []

        items: list[Any] = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("results") or data.get("events") or data.get("data") or []

        out: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            # Map GDG Community Dev JSON keys → our canonical field names.
            ev: dict[str, Any] = {
                "title": item.get("title") or item.get("name"),
                "start_at": item.get("start_date") or item.get("start_at") or item.get("datetime"),
                "end_at": item.get("end_date") or item.get("end_at"),
                "description": item.get("description") or item.get("summary"),
                "canonical_url": item.get("url") or item.get("event_url") or item.get("absolute_url") or page.url,
                "registration_url": item.get("url") or item.get("event_url"),
                "mode": _infer_mode(item),
                "city": item.get("city") or _extract_city(item),
                "venue_name": _extract_venue(item),
                "community_name": item.get("chapter_title") or item.get("group_name"),
                "organizer_name": item.get("organizer") or item.get("host"),
                "poster_url": item.get("banner_url") or item.get("image_url") or item.get("logo"),
                "is_free": item.get("is_free", True),
                "event_type": "meetup",
                "source_platform": "gdg",
                "_id": item.get("id") or item.get("pk"),
            }
            out.append(ev)
        return out

    def get_external_id(self, raw: dict[str, Any]) -> str | None:
        v = raw.get("_id")
        return str(v) if v is not None else None


def _infer_mode(item: dict[str, Any]) -> str:
    raw = (
        str(item.get("event_type", ""))
        + " "
        + str(item.get("type", ""))
        + " "
        + str(item.get("mode", ""))
    ).lower()
    if "online" in raw or "virtual" in raw or "remote" in raw:
        return "online"
    if "hybrid" in raw:
        return "hybrid"
    return "offline"


def _extract_city(item: dict[str, Any]) -> str | None:
    venue = item.get("venue") or {}
    if isinstance(venue, dict):
        return venue.get("city") or venue.get("address_city")
    return None


def _extract_venue(item: dict[str, Any]) -> str | None:
    venue = item.get("venue") or {}
    if isinstance(venue, dict):
        return venue.get("name") or venue.get("venue_name")
    if isinstance(venue, str):
        return venue
    return item.get("location") or item.get("venue_name")


async def _jitter() -> None:
    """Random 0.5–2.0s delay between requests to be a polite scraper."""
    import asyncio
    await asyncio.sleep(random.uniform(0.5, 2.0))
