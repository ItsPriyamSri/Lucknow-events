from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import get_current_admin
from api.schemas.admin import (
    AdminEventListResponse,
    AdminEventOut,
    EventUpdate,
)
from api.schemas.event import EventDetailResponse
from api.services import admin_service


router = APIRouter()
Admin = Annotated[dict, Depends(get_current_admin)]


@router.get("", response_model=AdminEventListResponse)
async def list_all_events(
    admin: Admin,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List ALL events (including unpublished/expired) for admin review."""
    items, total = await admin_service.list_all_events(db, page=page, limit=limit, q=q)
    return AdminEventListResponse(items=items, page=page, limit=limit, total=total)


@router.put("/{event_id}", response_model=EventDetailResponse)
async def update_event(
    event_id: str,
    payload: EventUpdate,
    admin: Admin,
    db: AsyncSession = Depends(get_db),
):
    """Full update of event details from admin dashboard."""
    ev = await admin_service.update_event(
        db, event_id, {k: v for k, v in payload.model_dump().items() if v is not None}
    )
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


@router.post("/{event_id}/rescrape", status_code=202)
async def rescrape_event(
    event_id: str,
    admin: Admin,
    db: AsyncSession = Depends(get_db),
):
    """Re-trigger the ingestion pipeline for the source of a specific event."""
    from api.models.event import Event
    from sqlalchemy import select

    # Find the source_id from the event's source
    ev = await db.get(Event, event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Find the source linked to this event via canonical_url or source tracking
    from api.models.source import Source
    res = await db.execute(
        select(Source).where(Source.base_url == ev.canonical_url).limit(1)
    )
    src = res.scalars().first()

    if src is None:
        # Fallback: try to match via raw_events table
        raise HTTPException(
            status_code=422,
            detail="Could not find associated source for this event. Try crawling the source directly."
        )

    from workers.tasks.pipeline import run_pipeline_for_source
    task = run_pipeline_for_source.delay(str(src.id))
    return {"task_id": task.id, "source_id": str(src.id), "event_id": event_id}


@router.patch("/{event_id}/feature", response_model=EventDetailResponse)
async def feature_event(
    event_id: str,
    featured: bool = True,
    admin: Admin = None,
    db: AsyncSession = Depends(get_db),
):
    ev = await admin_service.feature_event(db, event_id, featured)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


@router.patch("/{event_id}/cancel", response_model=EventDetailResponse)
async def cancel_event(
    event_id: str,
    admin: Admin = None,
    db: AsyncSession = Depends(get_db),
):
    ev = await admin_service.cancel_event(db, event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    admin: Admin = None,
    db: AsyncSession = Depends(get_db),
):
    deleted = await admin_service.delete_event(db, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
