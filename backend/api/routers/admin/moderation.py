from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import get_current_admin
from api.schemas.admin import ModerationItemOut
from api.services import admin_service


router = APIRouter()
Admin = Annotated[dict, Depends(get_current_admin)]


@router.get("", response_model=list[ModerationItemOut])
async def list_pending(admin: Admin, db: AsyncSession = Depends(get_db)):
    return await admin_service.list_pending_moderation(db)


@router.post("/{item_id}/approve", response_model=ModerationItemOut)
async def approve(item_id: str, admin: Admin, db: AsyncSession = Depends(get_db)):
    item = await admin_service.resolve_moderation(db, item_id, "approved")
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/{item_id}/reject", response_model=ModerationItemOut)
async def reject(item_id: str, admin: Admin, db: AsyncSession = Depends(get_db)):
    item = await admin_service.resolve_moderation(db, item_id, "rejected")
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
