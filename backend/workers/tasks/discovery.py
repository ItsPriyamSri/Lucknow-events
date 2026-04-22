"""Celery task: Automated Agent to discover Lucknow tech events via Gemini."""
from __future__ import annotations

import asyncio
from typing import Any

import structlog
from celery import shared_task
from google.genai import types
from pydantic import BaseModel

from api.core.database import SessionLocal

log = structlog.get_logger(__name__)


class DiscoveryResult(BaseModel):
    event_urls: list[str]


@shared_task(
    bind=True,
    name="workers.tasks.discovery.auto_discover_events",
    max_retries=1,
)
def auto_discover_events(self) -> dict[str, Any]:
    """Scheduled task to find new event URLs via AI and queue them for validation."""
    return asyncio.get_event_loop().run_until_complete(_async_discover())


async def _async_discover() -> dict[str, Any]:
    from ai.gemini_client import get_client
    from api.models.source import Source
    from api.services.submission_service import create_submission
    from sqlalchemy import select

    import datetime

    client = get_client()

    # Calculate current month + next 5 months
    now = datetime.datetime.now()
    months = []
    for i in range(6):
        m = (now.month - 1 + i) % 12 + 1
        y = now.year + (now.month - 1 + i) // 12
        date_obj = datetime.date(y, m, 1)
        months.append(date_obj.strftime("%B %Y"))
    
    months_str = " OR ".join(f'"{m}"' for m in months)

    queries = [
        f'Search using this exact query: (site:lu.ma OR site:commudle.com OR site:unstop.com/hackathons) "Lucknow" AND ({months_str}). Output ONLY a raw JSON mapping strictly matching the schema with no markdown formatting.',
        f'Search using this exact query: (intitle:hackathon OR intitle:fest) (Amity OR IET OR BBD OR SRM) Lucknow ({months_str}). Output ONLY a raw JSON mapping strictly matching the schema with no markdown formatting.',
        f'Search using this exact query: "GDG Lucknow" OR "AWS User Group Lucknow" OR "TFUG Lucknow" upcoming events in ({months_str}). Output ONLY a raw JSON mapping strictly matching the schema with no markdown formatting.',
        f'Search using this exact query: "tech networking" OR "AI workshop" OR "startup pitch" Lucknow ({months_str}). Output ONLY a raw JSON mapping strictly matching the schema with no markdown formatting.'
    ]

    async def fetch_urls(prompt: str) -> list[str]:
        try:
            response = await client.aio.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_mime_type="application/json",
                    response_json_schema=DiscoveryResult.model_json_schema(),
                    temperature=0.3,
                )
            )
            parsed = DiscoveryResult.model_validate_json(response.text)
            return parsed.event_urls
        except Exception as exc:
            log.warning("discovery.query_error", error=str(exc))
            return []

    # Execute all searches concurrently
    results_lists = await asyncio.gather(*(fetch_urls(q) for q in queries))
    
    # Flatten and deduplicate in memory
    urls = list(set([url for sublist in results_lists for url in sublist]))
    
    results = {"total_found": len(urls), "new": 0, "duplicate": 0, "error": 0}
    log.info("discovery.search_success", total_urls=len(urls))

    async with SessionLocal() as db:
        for url in urls:
            try:
                # 1. Skip duplicate URLs
                stmt = select(Source).filter(Source.base_url == url)
                res = await db.execute(stmt)
                if res.scalars().first():
                    results["duplicate"] += 1
                    continue

                # 2. Add via submission service (which queues the AI gate task)
                await create_submission(
                    db,
                    event_url=url,
                    submitter_name="AI Discovery Agent",
                    submitter_email="agent@nawab.ai",
                    notes="Automatically discovered via Gemini Search Grounding"
                )
                results["new"] += 1

            except Exception as e:
                log.warning("discovery.process_url_failed", url=url, error=str(e))
                results["error"] += 1

    log.info("discovery.completed", **results)
    return results
