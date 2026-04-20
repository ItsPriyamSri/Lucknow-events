from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.crawl import CrawlRun
from api.models.event import Event
from api.models.moderation import ModerationQueueItem
from api.models.source import Source


# ─── Sources ─────────────────────────────────────────────────────────────────

async def list_sources(db: AsyncSession) -> list[Source]:
    res = await db.execute(select(Source).order_by(Source.created_at.desc()))
    return res.scalars().all()


async def get_source(db: AsyncSession, source_id: str) -> Source | None:
    return await db.get(Source, source_id)


async def create_source(db: AsyncSession, data: dict) -> Source:
    src = Source(**data)
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return src


async def patch_source(db: AsyncSession, source_id: str, data: dict) -> Source | None:
    src = await db.get(Source, source_id)
    if src is None:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(src, k, v)
    await db.commit()
    await db.refresh(src)
    return src


async def list_crawl_runs(db: AsyncSession, limit: int = 50) -> list[CrawlRun]:
    res = await db.execute(select(CrawlRun).order_by(CrawlRun.started_at.desc()).limit(limit))
    return res.scalars().all()


# ─── Moderation ──────────────────────────────────────────────────────────────

async def list_pending_moderation(db: AsyncSession) -> list[ModerationQueueItem]:
    res = await db.execute(
        select(ModerationQueueItem)
        .where(ModerationQueueItem.status == "pending")
        .order_by(ModerationQueueItem.created_at.asc())
    )
    return res.scalars().all()


async def resolve_moderation(db: AsyncSession, item_id: str, decision: str) -> ModerationQueueItem | None:
    item = await db.get(ModerationQueueItem, item_id)
    if item is None:
        return None
    item.status = decision  # "approved" or "rejected"
    item.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)
    return item


# ─── Events (admin actions) ───────────────────────────────────────────────────

async def feature_event(db: AsyncSession, event_id: str, featured: bool) -> Event | None:
    ev = await db.get(Event, event_id)
    if ev is None:
        return None
    ev.is_featured = featured
    await db.commit()
    await db.refresh(ev)
    return ev


async def cancel_event(db: AsyncSession, event_id: str) -> Event | None:
    ev = await db.get(Event, event_id)
    if ev is None:
        return None
    ev.is_cancelled = True
    await db.commit()
    await db.refresh(ev)
    return ev


async def delete_event(db: AsyncSession, event_id: str) -> bool:
    ev = await db.get(Event, event_id)
    if ev is None:
        return False
    await db.delete(ev)
    await db.commit()
    return True


# ─── Stats ────────────────────────────────────────────────────────────────────

async def get_stats(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    week_ahead = now + timedelta(days=7)

    events_total = (
        await db.execute(select(func.count()).select_from(Event).where(Event.published_at.is_not(None)))
    ).scalar_one()

    events_this_week = (
        await db.execute(
            select(func.count()).select_from(Event).where(
                (Event.published_at.is_not(None))
                & (Event.start_at >= now)
                & (Event.start_at <= week_ahead)
            )
        )
    ).scalar_one()

    pending_moderation = (
        await db.execute(
            select(func.count()).select_from(ModerationQueueItem).where(
                ModerationQueueItem.status == "pending"
            )
        )
    ).scalar_one()

    sources_active = (
        await db.execute(select(func.count()).select_from(Source).where(Source.enabled == True))  # noqa: E712
    ).scalar_one()

    return {
        "events_total": int(events_total),
        "events_this_week": int(events_this_week),
        "pending_moderation": int(pending_moderation),
        "sources_active": int(sources_active),
    }
