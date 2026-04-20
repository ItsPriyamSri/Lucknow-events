# Source Adapters

## Adapter interface
Defined in `backend/ingestion/adapters/base.py`:
- `fetch(source) -> list[ScrapedPage]`
- `extract_raw_events(page) -> list[dict]`
- `get_external_id(raw) -> str | None`

## GDG (MVP)
File: `backend/ingestion/adapters/gdg.py`

Strategy:
- Attempt chapter-based JSON endpoint (may change over time).
- If it breaks, switch to Playwright-based scraping of chapter listing + details (planned).

## Generic HTML (planned)
Strategy:
- Playwright render
- Visible text extraction + cleanup
- Gemini Extraction Agent as primary parser

