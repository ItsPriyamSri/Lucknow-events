from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

import structlog
from celery import shared_task
from sqlalchemy import select

from api.core.database import SessionLocal
from api.models.source import Source
from api.models.submission import ManualSubmission
from workers.utils import run_async

log = structlog.get_logger(__name__)


@shared_task(name="workers.tasks.submissions.process_manual_submission")
def process_manual_submission(submission_id: str) -> dict:
    """
    End-to-end handling for user-submitted event links.

    Flow:
    - create a temporary `Source` (generic adapter) for the submitted URL
    - run the normal ingestion pipeline for that source
    - if an event is published, keep the source enabled (future crawls)
    - otherwise, disable the source and mark submission as skipped/rejected
    """

    from ingestion.pipeline import run_source_pipeline

    async def _run() -> dict:
        async with SessionLocal() as db:
            submission = await db.get(ManualSubmission, submission_id)
            if submission is None:
                return {"ok": False, "error": "submission_not_found"}

            url = (submission.event_url or "").strip()
            if not url:
                submission.status = "invalid"
                await db.commit()
                return {"ok": False, "error": "missing_url"}

            submission.status = "processing"
            await db.commit()

            # Create a Source for this URL so future crawls can track changes/new events.
            host = urlparse(url).netloc or "user-submitted"
            src = Source(
                name=f"User submitted: {host}",
                platform="generic",
                base_url=url,
                crawl_strategy="playwright",
                enabled=True,  # will be disabled if not a publishable tech event
                crawl_interval_hours=1,
                trust_score=0.70,
                config_json={"submitted_via": "manual_submission", "submission_id": submission_id},
                last_crawled_at=None,
                last_success_at=None,
                last_failure_at=None,
                consecutive_failures=0,
            )
            db.add(src)
            await db.flush()
            await db.commit()

            try:
                counts = await run_source_pipeline(str(src.id))
            except Exception as exc:
                log.exception("submission.pipeline_failed", submission_id=submission_id, error=str(exc))
                submission.status = "failed"
                src.enabled = False
                src.last_failure_at = datetime.now(timezone.utc)
                await db.commit()
                return {"ok": False, "error": "pipeline_failed"}

            published = int(counts.get("events_published") or 0)
            queued = int(counts.get("events_queued") or 0)

            if published > 0:
                submission.status = "accepted"
                await db.commit()
                return {"ok": True, "status": "accepted", "source_id": str(src.id), **counts}

            # Not publishable (not an event, too low confidence, irrelevant, etc.)
            # Keep the Source disabled so it does not pollute future crawls.
            src.enabled = False
            submission.status = "skipped" if queued == 0 else "needs_review"
            await db.commit()
            return {"ok": True, "status": submission.status, "source_id": str(src.id), **counts}

    return run_async(_run())

