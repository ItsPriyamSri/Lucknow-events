# AI Extraction (Gemini)

## Purpose
When deterministic scraping fails or yields incomplete fields, we use Gemini Flash in **native JSON mode** to extract a single event record from page text.

## Implementation
- Client wrapper: `backend/ai/gemini_client.py`
- Agents:
  - `backend/ai/extraction_agent.py`
  - `backend/ai/classification_agent.py`
  - `backend/ai/moderation_agent.py`

## JSON-mode contract
We request JSON responses using:
- `response_mime_type="application/json"`
- `response_json_schema=<PydanticModel>`

This is more reliable than prompt-only JSON.

## Safety / reliability rules
- Never invent facts: missing info stays `null`.
- Every call must be wrapped with error handling; hard failures route to moderation (post-MVP wiring).
- Keep input text bounded (target ~8000 chars after cleaning) to control cost and failure rate.

