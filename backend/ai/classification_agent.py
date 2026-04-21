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
    if settings.AI_MODE.lower() == "mock":
        return _mock_classify(inp)

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
    try:
        resp = await client.aio.models.generate_content(
            model=model,
            contents=str(user_prompt),
            config=json_config(GeminiClassificationOutput).model_copy(update={"system_instruction": SYSTEM_PROMPT}),
        )
        parsed = getattr(resp, "parsed", None)
        if parsed is not None:
            return (
                parsed
                if isinstance(parsed, GeminiClassificationOutput)
                else GeminiClassificationOutput.model_validate(parsed)
            )
        return GeminiClassificationOutput.model_validate_json(resp.text)
    except Exception:
        if settings.AI_FALLBACK_TO_MOCK:
            return _mock_classify(inp)
        raise


def _mock_classify(inp: ClassificationInput) -> GeminiClassificationOutput:
    import re

    text = (inp.title or "") + "\n" + (inp.description or "")
    topics: list[str] = []
    if re.search(r"\\bpython\\b", text, re.IGNORECASE):
        topics.append("python")
    if re.search(r"\\bjavascript\\b|\\bjs\\b|\\breact\\b", text, re.IGNORECASE):
        topics.append("javascript")
    if re.search(r"\\bai\\b|\\bml\\b|machine learning", text, re.IGNORECASE):
        topics.append("ai")

    event_type = "meetup"
    if re.search(r"hackathon", text, re.IGNORECASE):
        event_type = "hackathon"
    elif re.search(r"workshop", text, re.IGNORECASE):
        event_type = "workshop"
    elif re.search(r"conference|summit", text, re.IGNORECASE):
        event_type = "conference"

    return GeminiClassificationOutput(
        event_type=event_type,
        topics=topics[:5],
        audience=[],
        is_student_friendly=bool(re.search(r"student", text, re.IGNORECASE)),
        lucknow_relevance_score=0.7 if re.search(r"\\blacknow\\b", text, re.IGNORECASE) else 0.4,
        confidence=0.4,
    )

