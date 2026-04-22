"""Celery task: Automated Agent to discover Lucknow tech events via Gemini Search Grounding."""
from __future__ import annotations

import asyncio
import datetime
from typing import Any

import structlog
from celery import shared_task
from google.genai import types
from pydantic import BaseModel

from api.core.database import SessionLocal

log = structlog.get_logger(__name__)


class DiscoveryResult(BaseModel):
    event_urls: list[str]


def _build_month_window(months: int = 4) -> tuple[list[str], str]:
    """Return a list of 'Month YYYY' strings and a query-friendly OR string for the next N months."""
    now = datetime.datetime.now()
    month_labels = []
    for i in range(months):
        m = (now.month - 1 + i) % 12 + 1
        y = now.year + (now.month - 1 + i) // 12
        date_obj = datetime.date(y, m, 1)
        month_labels.append(date_obj.strftime("%B %Y"))
    months_str = " OR ".join(f'"{m}"' for m in month_labels)
    return month_labels, months_str


@shared_task(
    bind=True,
    name="workers.tasks.discovery.auto_discover_events",
    max_retries=1,
)
def auto_discover_events(self, custom_queries: list[str] | None = None) -> dict[str, Any]:
    """Scheduled task to find new event URLs via AI and queue them for validation.

    Args:
        custom_queries: Optional list of custom search queries to run (admin override).
    """
    return asyncio.get_event_loop().run_until_complete(_async_discover(custom_queries))


async def _async_discover(custom_queries: list[str] | None = None) -> dict[str, Any]:
    from ai.gemini_client import get_client
    from api.models.source import Source
    from api.services.submission_service import create_submission
    from sqlalchemy import select

    client = get_client()

    _, months_str = _build_month_window(months=4)  # Next 4 months only (quarterly window)

    # Default discovery queries — focused on real Lucknow event sources
    default_queries = [
        # Known Lucknow community platforms
        (
            f'Search: site:lu.ma "Lucknow" ({months_str}). '
            'Return ONLY a JSON list of direct event page URLs. No markdown.'
        ),
        (
            f'Search: site:commudle.com "lucknow" ({months_str}). '
            'Return ONLY a JSON list of direct event page URLs. No markdown.'
        ),
        (
            f'Search: site:unstop.com ("Lucknow" OR "IIIT Lucknow" OR "BBD" OR "SRMCEM" OR "Amity Lucknow") ({months_str}). '
            'Return ONLY a JSON list of direct event page URLs. No markdown.'
        ),
        # Known Lucknow communities with explicit names
        (
            f'Search: ("GDG Lucknow" OR "TFUG Lucknow" OR "FOSS United Lucknow" OR "AWS User Group Lucknow" OR "Lucknow AI Labs") '
            f'upcoming events ({months_str}). '
            'Return ONLY a JSON list of direct event page URLs. No markdown.'
        ),
        # College events
        (
            f'Search: ("IIIT Lucknow" OR "HackoFiesta" OR "AXIOS" OR "E-Summit Lucknow" OR "BBD Lucknow" OR "Integral University Lucknow") '
            f'tech event hackathon fest ({months_str}). '
            'Return ONLY a JSON list of direct event page URLs. No markdown.'
        ),
        # Broader Lucknow tech events
        (
            f'Search: (hackathon OR workshop OR conference OR meetup) Lucknow UP India ({months_str}) site:devfolio.co OR site:unstop.com OR site:lu.ma. '
            'Return ONLY a JSON list of direct event page URLs. No markdown.'
        ),
    ]

    queries = custom_queries if custom_queries else default_queries

    async def fetch_urls(prompt: str) -> list[str]:
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_mime_type="application/json",
                    response_json_schema=DiscoveryResult.model_json_schema(),
                    temperature=0.1,
                ),
            )
            parsed = DiscoveryResult.model_validate_json(response.text)
            return parsed.event_urls
        except Exception as exc:
            log.warning("discovery.query_error", error=str(exc))
            return []

    # Execute all searches concurrently
    results_lists = await asyncio.gather(*(fetch_urls(q) for q in queries))

    # Flatten, deduplicate, and filter valid HTTPS URLs
    seen: set[str] = set()
    urls: list[str] = []
    for sublist in results_lists:
        for url in sublist:
            if isinstance(url, str) and url.startswith("http") and url not in seen:
                seen.add(url)
                urls.append(url)

    results = {"total_found": len(urls), "new": 0, "duplicate": 0, "error": 0, "queries_run": len(queries)}
    log.info("discovery.search_success", total_urls=len(urls))

    async with SessionLocal() as db:
        for url in urls:
            try:
                # Skip duplicate URLs already known
                stmt = select(Source).filter(Source.base_url == url)
                res = await db.execute(stmt)
                if res.scalars().first():
                    results["duplicate"] += 1
                    continue

                # Queue via submission service (which runs the AI gate + pipeline)
                await create_submission(
                    db,
                    event_url=url,
                    submitter_name="AI Discovery Agent",
                    submitter_email="agent@nawab.ai",
                    notes="Automatically discovered via Gemini Search Grounding (4-month window)",
                )
                results["new"] += 1

            except Exception as e:
                log.warning("discovery.process_url_failed", url=url, error=str(e))
                results["error"] += 1

    log.info("discovery.completed", **results)
    return results
