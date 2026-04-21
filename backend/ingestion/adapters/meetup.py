"""Meetup: GraphQL (OAuth bearer) when configured; else Playwright on public find-events pages."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from ingestion.adapters.base import BaseAdapter, ScrapedPage
from ingestion.adapters.playwright_util import (
    USER_AGENT,
    httpx_fetch_text,
    playwright_fetch_html,
    playwright_render,
)

log = structlog.get_logger(__name__)

_MEETUP_GQL = "https://api.meetup.com/gql-ext"


class MeetupAdapter(BaseAdapter):
    platform = "meetup"
    crawl_strategy = "graphql_or_playwright"

    async def fetch(self, source: dict[str, Any]) -> list[ScrapedPage]:
        cfg = source.get("config_json") or {}
        token = cfg.get("access_token") or os.getenv("MEETUP_ACCESS_TOKEN") or os.getenv("MEETUP_OAUTH_TOKEN")
        max_items = int(cfg.get("max_items", 15))
        now = datetime.now(timezone.utc)

        if token:
            pages = await self._fetch_graphql(source, token, max_items, now)
            if pages:
                return pages

        # Playwright: configurable search URL (Lucknow, India)
        find_url = cfg.get("find_url") or (
            "https://www.meetup.com/find/?source=EVENTS&location=in--Lucknow--India&distance=twentyFiveMiles"
        )
        # Meetup find pages are client-rendered; use rendered HTML for href discovery.
        listing_html = await httpx_fetch_text(find_url)
        if len(listing_html) < 1000:
            listing_html = await playwright_fetch_html(find_url, post_load_wait_ms=3500)

        href_re = re.compile(
            r'href="(https://www\.meetup\.com/[^"/]+/events/[^"/]+/?)"',
            re.I,
        )
        seen: set[str] = set()
        links: list[str] = []
        for m in href_re.finditer(listing_html):
            u = m.group(1).split("?")[0]
            if u not in seen:
                seen.add(u)
                links.append(u)
            if len(links) >= max_items:
                break

        pages: list[ScrapedPage] = []
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

    async def _fetch_graphql(
        self, source: dict[str, Any], token: str, max_items: int, now: datetime
    ) -> list[ScrapedPage]:
        """Best-effort GraphQL search; schema may change — failures return []."""
        query = """
        query ($first: Int!) {
          rankedSearch(filter: { query: "tech", lat: 26.85, lon: 80.95, radius: 50 }) {
            edges { node { id title dateTime eventUrl description } }
          }
        }
        """
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                r = await client.post(
                    _MEETUP_GQL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"query": query, "variables": {"first": max_items}},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            log.warning("meetup.graphql_failed", error=str(exc))
            return []

        pages: list[ScrapedPage] = []
        try:
            edges = data.get("data", {}).get("rankedSearch", {}).get("edges", [])
            for edge in edges[:max_items]:
                node = (edge or {}).get("node") or {}
                title = node.get("title")
                url = node.get("eventUrl")
                start = node.get("dateTime")
                desc = node.get("description")
                if not title or not url:
                    continue
                raw = {
                    "title": title,
                    "canonical_url": url,
                    "start_at": start,
                    "description": desc,
                    "community_name": "Meetup",
                }
                pages.append(
                    ScrapedPage(
                        url=url,
                        html_or_json=json.dumps(raw, ensure_ascii=False),
                        fetched_at=now,
                        status_code=200,
                        page_type="api_response",
                    )
                )
        except Exception as exc:
            log.warning("meetup.graphql_parse_failed", error=str(exc))
        return pages

    def extract_raw_events(self, page: ScrapedPage) -> list[dict[str, Any]]:
        if page.page_type == "api_response":
            try:
                return [json.loads(str(page.html_or_json))]
            except Exception:
                pass
        from ingestion.normalizers.text import MAX_EXTRACTION_CHARS, clean_text

        text = clean_text(str(page.html_or_json), max_chars=MAX_EXTRACTION_CHARS)
        return [{"_cleaned_text": text, "canonical_url": page.url}]

    def get_external_id(self, raw: dict[str, Any]) -> str | None:
        u = raw.get("canonical_url") or raw.get("url")
        if u and "meetup.com" in str(u):
            parts = [p for p in str(u).rstrip("/").split("/") if p]
            if parts:
                return parts[-1][:200]
        return None
