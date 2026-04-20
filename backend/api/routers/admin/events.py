from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import get_current_admin
from api.schemas.event import EventDetailResponse
from api.services import admin_service


router = APIRouter()
Admin = Annotated[dict, Depends(get_current_admin)]


@router.patch("/{event_id}/feature", response_model=EventDetailResponse)
async def feature_event(event_id: str, featured: bool = True, admin: Admin = None, db: AsyncSession = Depends(get_db)):
    ev = await admin_service.feature_event(db, event_id, featured)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


@router.patch("/{event_id}/cancel", response_model=EventDetailResponse)
async def cancel_event(event_id: str, admin: Admin = None, db: AsyncSession = Depends(get_db)):
    ev = await admin_service.cancel_event(db, event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str, admin: Admin = None, db: AsyncSession = Depends(get_db)):
    deleted = await admin_service.delete_event(db, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
