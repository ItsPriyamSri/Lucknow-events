## Project context — Lucknow Tech Events

### What we’re building
A production-ready **tech events aggregation platform for Lucknow, India**. It automatically discovers events across multiple sources, converts raw pages into a strict event schema, stores canonical events in Postgres, and presents them in a polished UI that looks like a native extension of the existing Lucknow Developers community website.

- **Core product promise**: every event card + detail page has a prominent **Register Now →** button that opens the **original registration page** (no re-registration on our platform).
- **Operating constraint**: ship a **functional MVP in 5 days**, then expand step-by-step without breaking the core flow.

### Delivery strategy (3 phases from the original brief)
- **Phase 1 — Backend first (MVP-critical)**: scraper + AI extraction + pipeline + API + feeds. This is the “data engine” that must be reliable.
- **Phase 2 — Frontend fully integrated**: Next.js 15 frontend built from **user-provided screenshots/theme** and integrated with the backend API.
- **Phase 3 — Expand gradually**: more sources, richer admin, search/calendar/SEO polish and continuous improvements post-launch.

### System architecture (single monorepo)
```text
Scraper Layer (Python)                    Frontend (Next.js 15)
Playwright + httpx                        Pages + components (SSR/ISR/CSR)
  ↓                                            ↑
AI Extraction/Enrichment (Gemini Flash)        REST API
Raw page → structured Event JSON               |
  ↓                                            |
Backend API (FastAPI) + PostgreSQL 16  ————→  Users
Stores sources, raw_events, events, crawls
  ↓
Celery + Beat (Redis) + Flower
Scheduled crawls + feed rebuilds
```

### Tech stack (non‑negotiable)
- **Scraping**: Python 3.12, Playwright (async), httpx
- **Backend**: FastAPI (async), SQLAlchemy 2.0 async + asyncpg, PostgreSQL 16
- **Migrations**: Alembic with async-native `env.py`
- **Tasks**: Celery 5 + Redis + Celery Beat (idempotent; JSON serialization only)
- **Frontend**: Next.js 15 App Router, TypeScript, Tailwind CSS, shadcn/ui
- **Dev environment**: Docker Compose
- **Storage**: Cloudflare R2 (prod) or local filesystem (dev) for snapshots/posters
- **Tooling**: uv (Python), pnpm (Node), ruff, ESLint + Prettier

### Verified 2026 Gemini integration details (important)
The requirements doc mentions older model/SDK names. The plan uses the current 2026 approach for reliability:

- **Model**: default `gemini-3-flash-preview` (env-overridable via `GEMINI_MODEL`)
- **SDK**: `google-genai` (`from google import genai`)
- **Structured JSON output**: enforce schema at the API layer using:
  - `response_mime_type="application/json"`
  - `response_json_schema=<PydanticModel>`

This is used for:
- **Extraction Agent**: raw page text → strict `EventJSON`
- **Classification Agent**: fill `event_type/topics/audience`, compute relevance hints
- **Moderation Agent**: triage manual submissions

### Data model (what the backend stores)
We implement the schema from the requirements doc, centered on:
- `sources` — scrape targets and health/config
- `raw_events` — every extracted event pre-canonicalization (raw + AI outputs + confidence/flags)
- `events` — canonical published events (slug, start/end, mode, topics, urls, poster, scores)
- `crawl_runs` — crawl history
- `moderation_queue` — human review items
- `manual_submissions` — user-submitted event URLs

`events` includes:
- `search_vector` TSVECTOR maintained by a Postgres trigger + GIN index for full-text search
- `registration_url` (primary CTA) with fallback to `canonical_url`

### Pipeline (end-to-end flow)
For each enabled source, the ingestion pipeline runs:
1. **Fetch** raw HTML/JSON (Playwright/httpx)
2. **Snapshot + SHA256 hash** (skip unchanged)
3. **Deterministic parsing** first (where possible)
4. **AI extraction/enrichment** when confidence is low or required fields are missing
5. **Normalize** dates (IST-aware), location, text, URLs
6. **Lucknow relevance scoring** (offline needs Lucknow venue; online/hybrid needs community relevance)
7. **Deduplication** (hash key + similarity window)
8. **Publish decision** into canonical `events` or send to moderation
9. **Feed rebuild** (JSON + ICS)

### Sources (MVP vs later)
- **MVP sources**:
  - **GDG** (primary “stable” source)
  - **Generic HTML** adapter (Playwright render → visible text → AI extraction primary)
- **Post-launch expansion (Phase 3)**: Meetup, Commudle, Devfolio, Unstop (Playwright/XHR intercept + deterministic parsing + AI fallback)

### Public product surface (MVP)
Backend:
- `GET /api/v1/events` (filters + pagination)
- `GET /api/v1/events/{slug}`
- `GET /api/v1/events/featured`, `/this-week`, `/student-friendly`
- `POST /api/v1/submissions` (rate-limited)
- Feeds: `GET /api/v1/feeds/events.json` and `GET /api/v1/feeds/events.ics`

Frontend (Next.js 15):
- `/` (home, SSR), `/events` (listing, SSR), `/events/[slug]` (detail, ISR 1h)
- `/submit`, `/about`, `/calendar` (basic MVP calendar view)

### UI / theming constraint
The frontend must look like an extension of the parent Lucknow Developers site:
- **Primary input**: screenshots/theme provided by the user
- **Approach**: derive a small set of design tokens (colors, typography, radii, shadows) and implement with Tailwind + shadcn/ui.

### Deployment target
- **Frontend**: Vercel
- **Backend stack**: single VPS with Docker Compose (api + worker + beat + Postgres + Redis + Caddy/Nginx), or managed Postgres/Redis if preferred.

### Non-negotiable quality rules
- **FastAPI DB URL**: must be `postgresql+asyncpg://...`
- **Alembic DB URL**: uses sync `postgresql+psycopg2://...` and async-native migration env
- **Celery**: idempotent tasks; JSON serialization only; never pickle
- **Logging**: `structlog`; no `print()` in production code
- **Resilience**: every Gemini call wrapped in try/except; failures route to moderation queue
- **Core UX invariant**: **Register Now →** always links to `registration_url ?? canonical_url`, opens in a new tab with `rel=\"noopener noreferrer\"`

### MVP “done” definition (acceptance)
- `make dev`, `make migrate`, `make seed` work on a clean machine
- A crawl produces at least one real published Lucknow event
- `GET /api/v1/events` returns real data
- Public listing + detail pages render and the Register Now links work
- ICS feed imports successfully into Google Calendar
- Manual submission → moderation queue → admin approve → event becomes visible publicly
