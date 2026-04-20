# Architecture

## Goal
Aggregate upcoming tech events relevant to Lucknow, India into a single page with a **direct registration link** for each event.

## Components

- **Scraper / ingestion (Python)**: fetches raw HTML/JSON from sources using `httpx` and/or Playwright.
- **AI extraction (Gemini Flash)**: converts raw page text into a strict JSON structure when deterministic parsing is incomplete.
- **Backend API (FastAPI)**: persists sources/events and serves public endpoints + feeds.
- **Worker layer (Celery + Beat)**: scheduled crawls and feed rebuilds (idempotent tasks, JSON serialization only).
- **Frontend (Next.js 15)**: SSR listing + ISR detail pages that feel like a section of the parent Lucknow Developers site.

## Data flow (crawl → publish)

```text
Source → Fetch (httpx/Playwright) → Snapshot+SHA256 → Raw extract → AI extract (conditional)
      → Normalize → Relevance score → Dedupe → Publish event → Feeds (JSON/ICS)
```

## Non-negotiables
- **Register Now →** must link to `registration_url` (fallback `canonical_url`) and open in new tab.
- FastAPI uses `postgresql+asyncpg://`; Alembic uses `postgresql+psycopg2://`.
- Celery tasks are idempotent and JSON-serialized (no pickle).

