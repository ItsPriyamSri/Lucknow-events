from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from ai.gemini_client import get_client, json_config
from api.core.config import settings


@dataclass(slots=True)
class ModerationInput:
    submitter_name: str | None
    submitter_email: str | None
    event_url: str
    notes: str | None
    poster_text: str | None = None


class GeminiModerationOutput(BaseModel):
    decision: str
    reason: str
    spam_likelihood: float
    tech_relevance: float


SYSTEM_PROMPT = """You triage manual event submissions for a Lucknow tech events platform.
Return JSON only with {decision, reason, spam_likelihood, tech_relevance}.
decision must be one of: approve, reject, human_review.
"""


async def triage_submission(inp: ModerationInput) -> GeminiModerationOutput:
    client = get_client()
    model = settings.GEMINI_MODEL
    payload = {
        "submitter_name": inp.submitter_name,
        "submitter_email": inp.submitter_email,
        "event_url": inp.event_url,
        "notes": inp.notes,
        "poster_text": inp.poster_text,
    }
    resp = await client.aio.models.generate_content(
        model=model,
        contents=[SYSTEM_PROMPT, str(payload)],
        config=json_config(GeminiModerationOutput),
    )
    if getattr(resp, "parsed", None) is not None:
        return resp.parsed
    return GeminiModerationOutput.model_validate_json(resp.text)

