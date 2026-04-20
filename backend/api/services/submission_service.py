from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from api.models.moderation import ModerationQueueItem
from api.models.submission import ManualSubmission


async def create_submission(
    db: AsyncSession,
    *,
    event_url: str,
    submitter_name: str | None,
    submitter_email: str | None,
    notes: str | None,
) -> ManualSubmission:
    submission = ManualSubmission(
        event_url=event_url,
        submitter_name=submitter_name,
        submitter_email=submitter_email,
        notes=notes,
    )
    db.add(submission)
    await db.flush()

    moderation = ModerationQueueItem(
        entity_type="manual_submission",
        entity_id=str(submission.id),
        reason="manual_submission",
        severity="low",
        status="pending",
    )
    db.add(moderation)

    await db.commit()
    await db.refresh(submission)
    return submission

