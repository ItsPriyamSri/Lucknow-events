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


SYSTEM_PROMPT = """You are a precise structured-data extraction agent for a Lucknow, India tech events aggregator.

Your SOLE task: Extract ONE tech event from the provided webpage text into strict JSON.

CRITICAL RULES:

1. DATES & TIMES are the #1 priority. You MUST extract the exact start date, start time, end date, and end time.
   - Format start_at and end_at as ISO 8601 strings with timezone offset, e.g. "2026-05-15T10:00:00+05:30".
   - Scan all text for date patterns: "15 May 2026", "May 15, 2026", "15/05/2026", "2026-05-15", "15th May", "April 30".
   - Scan for time patterns: "10:00 AM IST", "10:00 AM", "10 AM", "starts at 10", "10:00 - 14:00", "6 PM".
   - If only a date is found without a time, set time to 10:00:00+05:30 (common Lucknow event start) and add "time" to missing_fields.
   - If a date range like "May 15-17" is found: start_at = first day at 10:00, end_at = last day at 18:00.
   - All times should be in +05:30 (IST) unless another timezone is explicitly stated.
   - NEVER fabricate dates. If no date is present in the text, set start_at = null.

2. LOCATION: Set city = "Lucknow" ONLY if clearly stated or if the venue/organizer is known to be in Lucknow, UP, India.
   - Do not assume Lucknow — only set it when the text explicitly indicates it.
   - Extract venue_name (e.g. "IIIT Lucknow Auditorium"), locality (e.g. "Gomti Nagar"), and address if present.
   - mode must be one of: "offline", "online", or "hybrid". Look for keywords like "in-person", "virtual", "zoom", "webinar", "at venue".

3. REGISTRATION URL: Prefer the most direct registration/RSVP/ticket link. If none found, use the page URL.

4. EVENT DETECTION: Set not_an_event=true if the page is clearly NOT a single tech event:
   - Blog posts, news articles, product landing pages, job listings, listing/directory pages → not_an_event=true.
   - If it describes one specific, named, scheduled tech event → keep not_an_event=false.

5. PRICE: Look for "Free", "No fee", "₹0", "Paid", "₹", "Registration fee", "Entry fee".
   - is_free=true if free/no-cost. is_free=false if paid. Default is_free=true if completely unclear.
   - price_type: "free", "paid", or "unknown".

6. CONFIDENCE: Score 0.0–1.0:
   - 0.90+ : title + exact start date & time + venue/mode extracted
   - 0.70–0.89: title + start date (no time) + venue/mode
   - 0.50–0.69: title + start date only
   - 0.30–0.49: title only (date missing)
   - 0.00: not_an_event=true

7. MISSING_FIELDS: List field names you could NOT find: e.g. ["end_at", "venue_name", "time", "description"].

8. NEVER invent or hallucinate data. Return null for any field not present in the text.
   Do not use placeholder values like "TBD", "Unknown", or "N/A" — just return null."""


GROUNDED_SYSTEM_PROMPT = """You are a precise event data extraction agent for a Lucknow, India tech events aggregator.

Using Google Search, look up the exact event at the given URL and extract all event details.
Focus especially on: exact date, exact time (IST), venue in Lucknow, registration link, and price.

Rules:
- Format start_at and end_at as ISO 8601 with +05:30 timezone offset.
- Set city = "Lucknow" only if the event is in Lucknow, UP, India.
- If no date is found even after searching, set start_at = null.
- Return null for any field you genuinely cannot find.
- NEVER fabricate data."""


async def extract_event(inp: ExtractionInput) -> GeminiExtractionOutput:
    if settings.AI_MODE.lower() == "mock":
        return _mock_extract(inp)

    client = get_client()
    model = settings.GEMINI_MODEL

    # Heuristic: detect JS-heavy SPA pages that have no useful date signal.
    import re
    text_lower = inp.cleaned_text.lower()
    _DATE_KEYWORDS = (
        "date", "time", "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "2025", "2026", "2027", "starts", "ends", "register by", "am", "pm",
        "morning", "evening", "afternoon",
    )
    has_date_signal = any(kw in text_lower for kw in _DATE_KEYWORDS)
    is_js_soup = (
        not has_date_signal and
        (
            "window.__" in inp.cleaned_text or
            "@font-face" in inp.cleaned_text or
            len(inp.cleaned_text) > 4000
        )
    )

    user_prompt = (
        f"Source platform: {inp.source_platform}\n"
        f"Page URL: {inp.page_url}\n"
        f"Partial data already known: {inp.partial_hints}\n\n"
        f"--- PAGE TEXT START ---\n{inp.cleaned_text}\n--- PAGE TEXT END ---\n\n"
        "Extract the event data as JSON. Pay special attention to any dates and times mentioned."
    )

    if is_js_soup:
        # Scraped text is mostly JS boilerplate — use Google Search Grounding to
        # retrieve accurate event details (especially the real date/time).
        from google.genai import types
        grounded_prompt = (
            f"Find complete event details for this specific event page: {inp.page_url}\n\n"
            f"Known event title: {inp.partial_hints.get('title', 'unknown')}\n"
            f"Source platform: {inp.source_platform}\n\n"
            "Search for and extract the following EXACTLY:\n"
            "1. Event start date and start time (in IST / Asia/Kolkata timezone)\n"
            "2. Event end date and end time (if available)\n"
            "3. Venue name and full address in Lucknow (if offline/hybrid)\n"
            "4. Registration or RSVP URL\n"
            "5. Whether the event is free or paid (price if paid)\n"
            "6. A 2-3 sentence description of the event\n"
            "7. Organizer name or community name\n\n"
            "Return the event data as JSON matching the provided schema. "
            "If a field is not found even after searching, return null for that field."
        )
        try:
            resp = await client.aio.models.generate_content(
                model=model,
                contents=grounded_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_mime_type="application/json",
                    response_json_schema=GeminiExtractionOutput.model_json_schema(),
                    system_instruction=GROUNDED_SYSTEM_PROMPT,
                    temperature=0.1,
                ),
            )
            result = GeminiExtractionOutput.model_validate_json(resp.text)
            # Only use the grounded result if it produced a real date
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
        parsed = getattr(resp, "parsed", None)
        if parsed is not None:
            return (
                parsed
                if isinstance(parsed, GeminiExtractionOutput)
                else GeminiExtractionOutput.model_validate(parsed)
            )
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
