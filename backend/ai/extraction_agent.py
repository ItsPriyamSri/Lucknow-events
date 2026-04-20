from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from ai.gemini_client import get_client, json_config
from api.core.config import settings


@dataclass(slots=True)
class ExtractionInput:
    source_platform: str
    source_url: str
    page_url: str
    cleaned_text: str
    partial_hints: dict


class GeminiExtractionOutput(BaseModel):
    title: str | None = None
    description: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    timezone: str = "Asia/Kolkata"
    city: str | None = None
    locality: str | None = None
    venue_name: str | None = None
    address: str | None = None
    mode: str | None = None
    event_type: str | None = None
    topics: list[str] = Field(default_factory=list, max_length=5)
    audience: list[str] = Field(default_factory=list)
    organizer_name: str | None = None
    community_name: str | None = None
    registration_url: str | None = None
    price_type: str = "unknown"
    is_free: bool = True
    is_student_friendly: bool = False
    confidence: float = 0.0
    missing_fields: list[str] = Field(default_factory=list)
    not_an_event: bool = False


SYSTEM_PROMPT = """You are a structured data extraction service for a Lucknow, India tech events platform.

Your task: Extract one tech event from the provided webpage text into strict JSON.

Rules:
- Never invent facts. If a field is not present in the text, return null.
- city should be \"Lucknow\" only if clearly indicated.
- For registration_url: prefer the most direct registration link. If none, use the page URL.
- confidence: reflect how complete and certain your extraction is.
- If the page is clearly not a tech event, set not_an_event=true and confidence=0.0.
"""


async def extract_event(inp: ExtractionInput) -> GeminiExtractionOutput:
    client = get_client()
    model = settings.GEMINI_MODEL
    user_prompt = (
        f"Source platform: {inp.source_platform}\n"
        f"Page URL: {inp.page_url}\n"
        f"Partial data already known: {inp.partial_hints}\n\n"
        f"--- PAGE TEXT START ---\n{inp.cleaned_text}\n--- PAGE TEXT END ---\n\n"
        "Extract the event data as JSON."
    )

    resp = client.models.generate_content(
        model=model,
        contents=[SYSTEM_PROMPT, user_prompt],
        config=json_config(GeminiExtractionOutput),
    )
    # SDK returns parsed JSON in resp.parsed when response_json_schema is used.
    if getattr(resp, "parsed", None) is not None:
        return resp.parsed
    # fallback: validate from text
    return GeminiExtractionOutput.model_validate_json(resp.text)

