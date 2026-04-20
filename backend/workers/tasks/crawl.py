from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task
from sqlalchemy import select, update

from api.core.database import SessionLocal
from api.models.event import Event
from api.models.source import Source


log = structlog.get_logger(__name__)


@shared_task(name="workers.tasks.crawl.crawl_all_sources")
def crawl_all_sources() -> dict:
    """Enqueue a pipeline task for every enabled source."""

    async def _run() -> list[str]:
        async with SessionLocal() as db:
            res = await db.execute(select(Source).where(Source.enabled == True))  # noqa: E712
            sources = res.scalars().all()
            return [str(s.id) for s in sources]

    source_ids = asyncio.run(_run())
    log.info("crawl_all_sources.dispatching", count=len(source_ids))

    from workers.tasks.pipeline import run_pipeline_for_source

    for sid in source_ids:
        run_pipeline_for_source.delay(sid)

    return {"ok": True, "dispatched": len(source_ids)}


@shared_task(name="workers.tasks.crawl.expire_past_events")
def expire_past_events() -> dict:
    now = datetime.now(timezone.utc)

    async def _run() -> int:
        async with SessionLocal() as db:
            cutoff = now - timedelta(hours=48)
            stmt = (
                update(Event)
                .where(
                    (Event.expires_at.is_(None))
                    & (Event.end_at.is_not(None))
                    & (Event.end_at < cutoff)
                )
                .values(expires_at=now)
            )
            res = await db.execute(stmt)
            await db.commit()
            return int(res.rowcount or 0)

    updated = asyncio.run(_run())
    log.info("expire_past_events.done", updated=updated)
    return {"ok": True, "updated": updated}
