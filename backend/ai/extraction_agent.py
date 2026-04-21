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
    if settings.AI_MODE.lower() == "mock":
        return _mock_extract(inp)

    client = get_client()
    model = settings.GEMINI_MODEL
    user_prompt = (
        f"Source platform: {inp.source_platform}\n"
        f"Page URL: {inp.page_url}\n"
        f"Partial data already known: {inp.partial_hints}\n\n"
        f"--- PAGE TEXT START ---\n{inp.cleaned_text}\n--- PAGE TEXT END ---\n\n"
        "Extract the event data as JSON."
    )

    try:
        resp = await client.aio.models.generate_content(
            model=model,
            contents=user_prompt,
            config=json_config(GeminiExtractionOutput).model_copy(update={"system_instruction": SYSTEM_PROMPT}),
        )
        # SDK returns parsed JSON in resp.parsed when response_json_schema is used.
        parsed = getattr(resp, "parsed", None)
        if parsed is not None:
            # Some SDK versions return a plain dict here.
            return (
                parsed
                if isinstance(parsed, GeminiExtractionOutput)
                else GeminiExtractionOutput.model_validate(parsed)
            )
        # fallback: validate from text
        return GeminiExtractionOutput.model_validate_json(resp.text)
    except Exception:
        if settings.AI_FALLBACK_TO_MOCK:
            return _mock_extract(inp)
        raise


def _mock_extract(inp: ExtractionInput) -> GeminiExtractionOutput:
    """
    Heuristic fallback for dev when Gemini is unavailable (quota/network).
    Intentionally conservative: only fills what it can detect.
    """
    import re

    text = inp.cleaned_text or ""
    # Title: look for a labeled title-ish phrase.
    title = None
    m = re.search(r"(?:^|\\n)\\s*(?:event|title)\\s*[:\\-]\\s*(.+)", text, re.IGNORECASE)
    if m:
        title = m.group(1).strip()[:200]
    if not title:
        # fallback: first non-empty line
        for line in text.splitlines():
            s = line.strip()
            if s and len(s) >= 6:
                title = s[:200]
                break

    # URLs
    urls = re.findall(r"https?://\\S+", text)
    reg_url = None
    for u in urls:
        if any(k in u.lower() for k in ("register", "rsvp", "tickets", "ticket", "signup")):
            reg_url = u.rstrip(").,]")
            break
    if not reg_url and urls:
        reg_url = urls[0].rstrip(").,]")

    # Basic city heuristic
    city = "Lucknow" if re.search(r"\\blacknow\\b", text, re.IGNORECASE) else None

    not_an_event = False
    confidence = 0.35
    if title is None or len(title) < 6:
        not_an_event = True
        confidence = 0.0

    return GeminiExtractionOutput(
        title=title,
        description=text[:800] if text else None,
        start_at=None,
        end_at=None,
        city=city,
        locality=None,
        venue_name=None,
        address=None,
        mode=None,
        event_type=None,
        topics=[],
        audience=[],
        organizer_name=None,
        community_name=None,
        registration_url=reg_url or inp.page_url,
        price_type="unknown",
        is_free=True,
        is_student_friendly=False,
        confidence=confidence,
        missing_fields=[],
        not_an_event=not_an_event,
    )

