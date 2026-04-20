from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.submission import SubmissionCreateRequest, SubmissionCreateResponse
from api.services import submission_service


router = APIRouter()

limiter = Limiter(key_func=get_remote_address)


@router.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@router.post("", response_model=SubmissionCreateResponse)
@limiter.limit("5/hour")
async def create_submission(
    request: Request,
    payload: SubmissionCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    submission = await submission_service.create_submission(
        db,
        event_url=str(payload.event_url),
        submitter_name=payload.submitter_name,
        submitter_email=str(payload.submitter_email) if payload.submitter_email else None,
        notes=payload.notes,
    )
    return SubmissionCreateResponse(id=str(submission.id), status=submission.status)

