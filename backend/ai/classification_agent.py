from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from ai.gemini_client import get_client, json_config
from api.core.config import settings


@dataclass(slots=True)
class ClassificationInput:
    title: str
    description: str | None
    organizer_name: str | None
    community_name: str | None
    source_platform: str
    mode: str | None


class GeminiClassificationOutput(BaseModel):
    event_type: str | None = None
    topics: list[str] = Field(default_factory=list, max_length=5)
    audience: list[str] = Field(default_factory=list)
    is_student_friendly: bool = False
    lucknow_relevance_score: float = 0.5
    confidence: float = 0.0


SYSTEM_PROMPT = """You enrich already-extracted events for a Lucknow tech events platform.
Return JSON only. Never invent facts; infer cautiously from title/description.
"""


async def classify_event(inp: ClassificationInput) -> GeminiClassificationOutput:
    client = get_client()
    model = settings.GEMINI_MODEL
    user_prompt = {
        "title": inp.title,
        "description": inp.description,
        "organizer_name": inp.organizer_name,
        "community_name": inp.community_name,
        "source_platform": inp.source_platform,
        "mode": inp.mode,
    }
    resp = client.models.generate_content(
        model=model,
        contents=[SYSTEM_PROMPT, str(user_prompt)],
        config=json_config(GeminiClassificationOutput),
    )
    if getattr(resp, "parsed", None) is not None:
        return resp.parsed
    return GeminiClassificationOutput.model_validate_json(resp.text)

