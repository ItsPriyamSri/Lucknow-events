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

    # Heuristic: detect JS-heavy pages that have no useful date signal.
    # These are SPAs (Unstop, Devfolio, Commudle) that render as pure JS on the server.
    _USEFUL_SIGNAL_KEYWORDS = ("date", "time", "april", "may", "june", "july", "august",
                               "september", "october", "november", "december",
                               "january", "february", "march", "2026", "2027",
                               ":[0-9]", "starts", "ends", "register by")
    import re
    text_lower = inp.cleaned_text.lower()
    has_date_signal = any(kw in text_lower for kw in _USEFUL_SIGNAL_KEYWORDS)
    is_js_soup = (
        not has_date_signal and
        ("window." in inp.cleaned_text or "@font-face" in inp.cleaned_text or
         "var " in inp.cleaned_text or len(inp.cleaned_text) > 5000)
    )

    user_prompt = (
        f"Source platform: {inp.source_platform}\n"
        f"Page URL: {inp.page_url}\n"
        f"Partial data already known: {inp.partial_hints}\n\n"
        f"--- PAGE TEXT START ---\n{inp.cleaned_text}\n--- PAGE TEXT END ---\n\n"
        "Extract the event data as JSON."
    )

    if is_js_soup:
        # The scraped text is JS boilerplate — use Google Search Grounding to
        # retrieve accurate event details (especially the real date/time).
        from google.genai import types
        grounded_prompt = (
            f"Look up this specific event page on the web and extract structured event details: {inp.page_url}\n"
            f"Partial data already known: {inp.partial_hints}\n"
            "Find the exact event date, time, venue, description, and registration details. "
            "Return the event data as JSON."
        )
        try:
            resp = await client.aio.models.generate_content(
                model=model,
                contents=grounded_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_mime_type="application/json",
                    response_json_schema=GeminiExtractionOutput.model_json_schema(),
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                ),
            )
            result = GeminiExtractionOutput.model_validate_json(resp.text)
            # Only use the grounded result if it actually got a date
            if result.start_at and not result.not_an_event:
                return result
            # Fall through to standard extraction if grounding didn't help
        except Exception as exc:
            import structlog
            structlog.get_logger(__name__).warning("extraction.grounding_fallback_failed", error=str(exc))

    try:
        resp = await client.aio.models.generate_content(
            model=model,
            contents=user_prompt,
            config=json_config(GeminiExtractionOutput, system_instruction=SYSTEM_PROMPT),
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
    m = re.search(r"(?:^|\n)\s*(?:event|title)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
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
    urls = re.findall(r"https?://\S+", text)
    reg_url = None
    for u in urls:
        if any(k in u.lower() for k in ("register", "rsvp", "tickets", "ticket", "signup")):
            reg_url = u.rstrip(").,]")
            break
    if not reg_url and urls:
        reg_url = urls[0].rstrip(").,]")

    # Basic city heuristic
    city = "Lucknow" if re.search(r"\blucknow\b", text, re.IGNORECASE) else None

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

