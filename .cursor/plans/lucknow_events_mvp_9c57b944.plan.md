---
name: Lucknow Tech Events — 5-Day MVP
overview: Three-phase build of a Lucknow tech-events aggregator that ships a functional MVP in 5 days and plugs into the existing Lucknow Developers community website. Phase 1 delivers the backend core (scraper → Gemini 3 Flash extraction → FastAPI/Postgres/Celery pipeline with JSON+ICS feeds). Phase 2 builds the Next.js 15 frontend from user-provided screenshots of the parent site (Tailwind + shadcn/ui, screenshot-driven design tokens). Phase 3 (post-launch, rolling) expands source coverage (Meetup, Commudle, Devfolio, Unstop), enriches the admin dashboard, and adds search/calendar/SEO polish.
todos:
  - id: scaffold-monorepo
    content: Scaffold monorepo (backend/, apps/web/, docker/, scripts/, docs/), uv + pnpm, Docker Compose dev stack, Makefile, .env.example, ruff + ESLint/Prettier, pre-commit.
    status: completed
  - id: db-models-migrations
    content: Implement SQLAlchemy 2.0 async models for sources, raw_events, events, crawl_runs, moderation_queue, manual_submissions. Alembic async env.py. Initial migration creates tables, search_vector column, GIN index, and tsvector trigger on events.
    status: completed
  - id: api-public
    content: FastAPI app skeleton (lifespan, CORS, structlog, health). Public routers — events (list/detail/featured/this-week/student-friendly), feeds (events.json + events.ics), submissions (rate-limited). Services-only DB access; Pydantic v2 schemas.
    status: completed
  - id: admin-minimal
    content: JWT admin auth (login → bearer token). Minimal admin routers — sources (list/enable/disable/trigger-crawl), moderation (list/approve/reject), events (feature/cancel/delete), stats.
    status: completed
  - id: celery-scheduling
    content: Celery app + Redis + Beat with JSON-only serialization, idempotent tasks. Tasks for per-source crawl, full pipeline orchestration, feed rebuild, expire-past-events. Flower dashboard.
    status: completed
  - id: ingestion-core
    content: BaseAdapter + ScrapedPage dataclass, snapshot/hash storage (local for dev, R2 interface for prod), normalizers (date/location/text/url), location_data.py (Lucknow localities, institutions, communities), relevance scorer, dedup service, publish-score calculator.
    status: completed
  - id: ingestion-gdg-generic
    content: GDG adapter (primary JSON feed strategy with Playwright fallback) and Generic HTML adapter (Playwright render → cleaned text → AI extraction agent). Seed script inserts initial sources from requirements §17.
    status: completed
  - id: ai-gemini
    content: Gemini client using google-genai SDK (gemini-3-flash-preview default, env-overridable). Extraction Agent, Classification Agent, Moderation Agent — each with Pydantic response schemas via response_json_schema, retry-on-validate-fail, and fallback to moderation queue on hard failure. Invocation thresholds per requirements §7.5.
    status: completed
  - id: frontend-scaffold
    content: Next.js 16 (Turbopack) App Router + TypeScript + Tailwind CSS v4. Axios API client (lib/api.ts). Env wiring (NEXT_PUBLIC_API_URL). Root layout with Desktop Sidebar + Mobile sticky header.
    status: completed
  - id: frontend-theme-tokens
    content: "\"Nawab AI\" design tokens — deep mocha background (#1E1B18), muted gold primary (#D48C51), warm grays, 0.75rem radius. Encoded as @theme block in globals.css (Tailwind v4 CSS-first config). Inter font via next/font."
    status: completed
  - id: frontend-pages
    content: "All six pages shipped: `/` (hero + featured/this-week shelves), `/events` (SSR filter sidebar + card grid + clear-all), `/events/[slug]` (ISR detail with Register Now →), `/submit` (client form, 429-aware), `/calendar`, `/about`. EventCard and Sidebar components done."
    status: completed
  - id: frontend-seo
    content: generateMetadata per event (Open Graph + Twitter), sitemap.xml, robots.txt, JSON-LD Event schema on detail pages, Add-to-Calendar (per-event ICS download).
    status: completed
  - id: frontend-polish
    content: SWR on /events with router.replace (instant filter updates, keepPreviousData). Suspense + loading skeleton. Vercel Analytics in root layout. Google Calendar prefilled link on event detail. Docker NEXT_PUBLIC_API_URL includes /api/v1.
    status: completed
  - id: backend-communities-topics
    content: GET /api/v1/topics, /communities, /localities — FacetsListResponse with name+count from published events. discovery_service + discovery router.
    status: completed
  - id: alembic-initial-migration
    content: Committed Alembic revision 20260420120000_initial_schema.py creating all tables, partial unique index on raw_events, GIN on events.search_vector.
    status: completed
  - id: deploy-vercel-vps
    content: Vercel deploy for apps/web. VPS prod docker-compose for api + worker + beat + postgres + redis + Caddy reverse proxy with TLS. Env hardening, secrets, log rotation, healthchecks. Smoke checks against live endpoints.
    status: completed
  - id: docs
    content: Write docs/architecture.md, docs/ai-extraction.md, docs/source-adapters.md, docs/deployment.md — each kept accurate to shipped code.
    status: completed
  - id: post-mvp-sources
    content: Phase 3 source adapters — Meetup (GraphQL + Playwright fallback), Commudle (Playwright SPA), Devfolio (Playwright + XHR intercept), Unstop (internal API + Playwright fallback). Tune dedup and relevance thresholds.
    status: completed
  - id: post-mvp-polish
    content: Full admin dashboard (crawl history, raw events browser, events inline edit), PG full-text search wiring, featured/student-friendly shelves on home, communities + topics pages, empty-state CTAs.
    status: completed
isProject: false
---

## Phasing (mirrors the original brief)

The user's brief defined three phases; this plan compresses phases 1 and 2 into the 5-day launch and treats phase 3 as a rolling post-launch track.

1. **Phase 1 — Backend core.** Everything needed to ingest real Lucknow tech events end-to-end: scraper → Gemini extraction → normalization → publish → REST API + feeds.
2. **Phase 2 — Frontend built against the real backend.** Next.js 15 pages integrated with the backend API, styled from **user-provided screenshots** of the existing Lucknow Developers site so the new section reads as a natural extension.
3. **Phase 3 — Post-launch enhancements.** Broader source coverage, full admin dashboard, full search + calendar, SEO polish, moderation UX.

## Resolved technical ambiguities (verified 2026-04)

These supersede the corresponding details in the requirements doc because the doc was written against an older SDK/model lineup. Verified against the official Google GenAI Python SDK docs via Context7 and current Gemini API model list.

| Topic | Requirements doc | **Plan decision** | Rationale |
|---|---|---|---|
| Gemini model | `gemini-2.0-flash` | **`gemini-3-flash-preview`** (env-overridable via `GEMINI_MODEL`) | User asked for "Gemini Flash 3". `gemini-3-flash-preview` is the current 2026 API name. Keep env override so we can pin `gemini-2.5-flash` (stable) or `gemini-3.1-flash-lite-preview` (cheap) per environment. |
| Python SDK | `google-generativeai` | **`google-genai`** (`from google import genai`) | The unified SDK is the supported one going forward. It provides native structured output via `response_json_schema=<PydanticModel>` + `response_mime_type='application/json'`. |
| Structured JSON mode | Prompt + `response_mime_type` | **`response_mime_type='application/json'` + `response_json_schema=<PydanticModel>`** | Schema enforcement at the API level is stricter than prompt-only JSON mode and removes most validation retries. |

Everything else in the requirements doc (architecture layers, DB schema, endpoints, pipeline stages, ICS feed, admin routes, Docker Compose topology, deployment rules) is adopted verbatim unless this plan explicitly overrides it.

## MVP scope (what actually ships in 5 days)

**Ships in MVP:**
- Backend: all six tables + migrations, full public API (`/api/v1/events*`, `/api/v1/feeds/events.{json,ics}`, `/api/v1/submissions`, `/api/v1/communities`, `/api/v1/topics`), minimal admin (auth + sources + moderation approve/reject + feature/cancel/delete + stats).
- Ingestion: **GDG** adapter (primary) + **Generic HTML** adapter (AI-first). Full pipeline (fetch → snapshot+hash → raw extract → conditional AI → normalize → relevance → dedupe → publish → feed rebuild).
- AI: Extraction, Classification, and Moderation agents on `gemini-3-flash-preview` with Pydantic response schemas.
- Frontend: `/`, `/events`, `/events/[slug]`, `/submit`, `/about`, `/calendar` (basic). Screenshot-driven theme. Register Now → button on every card and detail page.
- Feeds: JSON + ICS, rebuilt hourly via Celery Beat.
- Ops: Docker Compose dev stack, Makefile targets, Alembic async migrations, structlog, Flower, seeded sources.

**Deferred to Phase 3 (post-launch, rolling):**
- Meetup / Commudle / Devfolio / Unstop adapters.
- Full admin dashboard (raw events browser, inline edit, featuring UX).
- Full-text search UX wiring, Open Graph images, sitemap, topics/communities pages.
- Monthly calendar interactions.

## Monorepo layout (target)

Exact structure from requirements doc §4. Key paths:

- [`backend/api/`](backend/api/) — FastAPI (`main.py`, `core/`, `models/`, `schemas/`, `routers/`, `services/`)
- [`backend/ingestion/`](backend/ingestion/) — `pipeline.py`, `adapters/`, `normalizers/`, `storage.py`, `location_data.py`
- [`backend/ai/`](backend/ai/) — `gemini_client.py`, `extraction_agent.py`, `classification_agent.py`, `moderation_agent.py`
- [`backend/workers/`](backend/workers/) — `celery_app.py`, `tasks/`, `schedules.py`
- [`backend/alembic/`](backend/alembic/) — `env.py` (async), `versions/`
- [`apps/web/`](apps/web/) — Next.js 15 App Router public site (+ `/admin` route)
- [`docker/`](docker/) — `docker-compose.dev.yml`, `docker-compose.prod.yml`
- [`scripts/`](scripts/) — `seed_sources.py`, `generate_openapi.py`
- [`docs/`](docs/) — architecture, ai-extraction, source-adapters, deployment
- `Makefile`, `.env.example`

## Database (exact schema per requirements §5)

- `sources`, `raw_events`, `events`, `crawl_runs`, `moderation_queue`, `manual_submissions` with UUID PKs and TIMESTAMPTZ timestamps.
- `events.search_vector` TSVECTOR populated by a trigger on INSERT/UPDATE:
  - `to_tsvector('english', coalesce(title,'') || ' ' || coalesce(short_description,'') || ' ' || coalesce(community_name,'') || ' ' || coalesce(organizer_name,'') || ' ' || coalesce(locality,''))`
  - GIN index: `idx_events_search`.
- Unique partial index on `raw_events(source_id, external_id) WHERE external_id IS NOT NULL`.
- All SQLAlchemy models use `Mapped[type]` + `mapped_column()` (2.0 style).
- `DATABASE_URL` uses `postgresql+asyncpg://`; `ALEMBIC_DATABASE_URL` uses `postgresql+psycopg2://`. Alembic `env.py` uses `async_engine_from_config` for online migrations.

## Ingestion pipeline (per event, per crawl)

Exact flow per requirements §8 — implemented in [`backend/ingestion/pipeline.py`](backend/ingestion/pipeline.py):

1. **Fetch** via adapter → `ScrapedPage(url, html_or_json, fetched_at, status_code, page_type)`.
2. **Snapshot + SHA256** → storage (`local` or `r2`). If hash unchanged since last crawl of this `(source_id, url)`, skip.
3. **Raw extract** deterministic (adapter `extract_raw_events`). Insert `raw_event` with `raw_payload_json`, `pipeline_status='pending'`, initial confidence.
4. **AI extraction (conditional)** per thresholds below. Merge AI output with deterministic output; deterministic fields win on conflict.
5. **Normalize** — date (IST-aware), location (Lucknow dictionary lookup), text (strip/truncate), URL (absolute, strip tracking params).
6. **Relevance score** — per requirements §11 function. Discard `< 0.3`; flag `0.3–0.5` for moderation.
7. **Dedupe** — key = `sha256(normalize(title) + date_bucket + normalize(organizer))`. Exact match → skip. Title similarity within ±12h → moderation.
8. **Publish decision** — weighted `publish_score`:
   - `≥ 0.80` → create `events` row, set `published_at = now()`, compute slug.
   - `0.55–0.79` → re-run Classification Agent, re-evaluate once.
   - `< 0.55` → insert into `moderation_queue`.
9. **Feed rebuild** — enqueue `workers.tasks.feeds.rebuild_all_feeds`.

### AI invocation thresholds (requirements §7.5)

| Condition | Action |
|---|---|
| Structured JSON source (GDG), all required fields present | Skip AI |
| Deterministic `parse_confidence ≥ 0.85` | Skip AI |
| `parse_confidence 0.60–0.84` | Classification Agent only |
| `parse_confidence < 0.60` | Extraction Agent → Classification Agent |
| Manual submission | Triage Agent always |
| Generic HTML adapter | Extraction Agent always (primary) |

## AI agents (Gemini 3 Flash via google-genai)

[`backend/ai/gemini_client.py`](backend/ai/gemini_client.py) — thin wrapper:

```python
from google import genai
from google.genai import types

_client: genai.Client | None = None

def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client

def json_config(schema: type) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=schema,
        temperature=0.1,
        max_output_tokens=2048,
    )
```

Each agent defines a **Pydantic v2 response model** and uses `response_json_schema=Model` so the API guarantees a parseable payload. Agents:

- [`backend/ai/extraction_agent.py`](backend/ai/extraction_agent.py) — `GeminiExtractionOutput` schema matching requirements §7.2 (title, start_at, end_at, venue, mode, event_type, topics, audience, registration_url, is_free, is_student_friendly, confidence, missing_fields, not_an_event). Retry once on validation failure with truncated input; on second failure route to moderation queue.
- [`backend/ai/classification_agent.py`](backend/ai/classification_agent.py) — enriches `event_type`, `topics` (≤5), `audience`, `is_student_friendly`, `lucknow_relevance_score`, `confidence`.
- [`backend/ai/moderation_agent.py`](backend/ai/moderation_agent.py) — triages manual submissions → `{decision, reason, spam_likelihood, tech_relevance}`.

All calls wrapped in try/except; failures emit structlog error and fall back to moderation queue.

## Source adapters (phasing)

**MVP (ships Day 2):**

- [`backend/ingestion/adapters/gdg.py`](backend/ingestion/adapters/gdg.py)
  - Primary: try GDG Community Dev public event JSON endpoint discovered from chapter page.
  - Fallback: Playwright render of chapter listing and event pages.
  - High trust (0.90–0.95). Deterministic parsing with AI only for missing description fields.
- [`backend/ingestion/adapters/generic.py`](backend/ingestion/adapters/generic.py)
  - Playwright headless render → extract visible text (cap 8000 chars) → Extraction Agent primary.
  - Used for one-off college and community pages registered manually.

**Phase 3 (post-launch):**

- `meetup.py` — Meetup GraphQL API (`POST https://api.meetup.com/gql-ext`) with OAuth2 bearer token; Playwright fallback on `meetup.com/find/events/?location=lucknow`.
- `commudle.py` — Playwright on `.community-event-card` with detail-page follow.
- `devfolio.py` — Playwright + `page.on("response", ...)` GraphQL XHR interception; HTML fallback.
- `unstop.py` — Internal API `GET https://unstop.com/api/opportunity/listing?location=Lucknow`; Playwright fallback.

**Scraping rules (all adapters):**
- Headless Playwright with `--no-sandbox` in Docker, realistic UA.
- `robots.txt` check before any new domain.
- Random 0.5–2.0s jitter between loads. Exponential backoff retries (max 3).
- SHA256 content hashing; snapshot raw payload before any processing.

## FastAPI routers (MVP)

**Public** — [`backend/api/routers/`](backend/api/routers/):

- `events.py` — `GET /api/v1/events` (q, start_date, end_date, mode, event_type, topic, locality, is_free, is_student_friendly, page, limit), `GET /events/{slug}`, `GET /events/featured`, `GET /events/this-week`, `GET /events/student-friendly`.
- `feeds.py` — `GET /feeds/events.json`, `GET /feeds/events.ics` (Content-Type: `text/calendar`, RFC 5545 via `icalendar` lib).
- `submissions.py` — `POST /submissions` (rate-limited 5/hr/IP via slowapi).
- `communities.py` — `GET /communities`, `GET /topics` with frequency counts.

**Admin** — [`backend/api/routers/admin/`](backend/api/routers/admin/) (JWT-protected):

- `auth.py` — `POST /admin/auth/login` → JWT (HS256, 60-min TTL). Admin credentials via `ADMIN_EMAIL` + bcrypt `ADMIN_PASSWORD_HASH`.
- `sources.py` — list, create, patch, `POST /crawl/run/{id}`, `POST /crawl/run-all`, `GET /crawl/runs`.
- `moderation.py` — list pending, approve, reject.
- `events.py` — feature, cancel, delete.
- `stats.py` — counts for dashboard.

**Architectural rule:** routers NEVER touch ORM directly — only call `backend/api/services/*`. Services accept `AsyncSession` and Pydantic domain models.

## Celery + scheduling

[`backend/workers/celery_app.py`](backend/workers/celery_app.py) with JSON-only serialization (no pickle). Beat schedule per requirements §9:

- `crawl-all-sources-every-6h` — `crontab(minute=0, hour="*/6")`
- `rebuild-feeds-every-hour` — `crontab(minute=30)`
- `expire-past-events-daily` — `crontab(hour=3, minute=0)` (sets `expires_at = end_at + 48h` and hides past events)

All tasks are idempotent (upserts with `ON CONFLICT`, hash-based skip).

## Frontend (Next.js 15, screenshot-driven theme)

**Theme extraction workflow** (runs before significant UI work):
1. User supplies screenshots of the existing Lucknow Developers site.
2. Derive design tokens: primary/secondary/accent colors, neutral scale, heading/body font families, font sizes, spacing scale, border radii, shadows.
3. Encode in Tailwind config (`theme.extend.colors/fonts/spacing`) and a small CSS variables layer in `app/globals.css`.
4. Build shadcn/ui components against the tokens. Use the saffron/navy/cream/teal palette from requirements §13.1 only as a fallback if screenshots aren't yet provided.

**Page map & rendering:**

| Page | Strategy | Notes |
|---|---|---|
| `/` | SSR | Hero, This Week shelf, Featured shelf, Student-Friendly shelf, topic pills, community logos, subscribe-to-ICS CTA |
| `/events` | SSR | Filters sidebar, event card grid, debounced search |
| `/events/[slug]` | ISR (revalidate: 3600) | Full details, prominent **Register Now →** (opens `registration_url ?? canonical_url` in new tab), related events, Add-to-Calendar |
| `/submit` | Client | Form POST to `/api/v1/submissions` with optional poster upload |
| `/about` | Static | Methodology + link to JSON feed |
| `/calendar` | Client | Monthly grid (basic for MVP) |
| `/admin/*` | Client | JWT-gated; built last in Phase 3 |

**Event Card component** — poster or color banner, event type badge, date chip, title (2-line clamp), community, 📍venue / online, 🕐 time, topic pills, FREE / Student-friendly chips, **Register Now →** (primary), **+ Calendar** (secondary).

**SEO:** `generateMetadata` per event page (OG title, description, image), JSON-LD `Event` schema, sitemap from published slugs, permissive `robots.txt`.

## Deployment

- **Frontend:** Vercel (Next.js 15). Env: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_NAME`, `NEXT_PUBLIC_SITE_URL`.
- **Backend:** single Docker VPS running `docker/docker-compose.prod.yml` with api + worker + beat + flower + postgres 16 + redis 7 + Caddy reverse proxy (auto-TLS). No bind mounts in prod. Healthchecks on all services. Log rotation via Docker's json-file driver with rotation limits.
- **Storage:** `STORAGE_TYPE=r2` in prod (Cloudflare R2 for poster snapshots + raw page snapshots). `local` in dev.
- **Secrets:** all via environment (`.env` on VPS, Vercel project env for web). Never commit secrets.

## Environment variables

Full list per requirements §14. Notable additions / adjustments made by this plan:

- `GEMINI_MODEL=gemini-3-flash-preview` — override to `gemini-2.5-flash` for stable-tier or `gemini-3.1-flash-lite-preview` for cheaper batch runs.
- `GEMINI_CLASSIFICATION_MODEL` optional override (defaults to same as `GEMINI_MODEL`).
- `GEMINI_MAX_INPUT_CHARS=8000` to keep token usage bounded.

## 5-day execution schedule

**Day 1 — Foundation**
- Scaffold monorepo, Docker Compose dev stack (`make dev` green).
- All DB models, Alembic async env, first migration with search_vector + trigger + GIN index.
- FastAPI skeleton (health, CORS, structlog, lifespan). `pydantic-settings` config.
- Celery + Redis + Beat: dummy periodic task runs and logs in Flower.
- Next.js 15 scaffold with Tailwind + shadcn/ui base install.

**Day 2 — Working data flow (backend vertical slice)**
- Seed sources script.
- GDG adapter + snapshot storage + pipeline (normalize → relevance → dedupe → publish).
- `GET /api/v1/events` (list + detail) returns real GDG Lucknow events.
- Frontend `/events` listing fetches real data (unstyled functional first). Event detail page renders with Register Now button.
- `/api/v1/feeds/events.ics` + `events.json` live.

**Day 3 — AI + submissions + minimal admin + theme start**
- Gemini client + Extraction/Classification/Moderation agents using `response_json_schema`.
- Generic HTML adapter using Extraction Agent primary.
- Submission endpoint + moderation queue + Triage Agent on every submission.
- JWT admin auth + approve/reject moderation endpoints.
- Frontend: collect user screenshots → derive design tokens → apply shadcn theme. Start home page hero + card component.

**Day 4 — Frontend sprint [✅ COMPLETED]**
- Scaffolded Next.js 16 (Turbopack) with Tailwind CSS v4 and Nawab AI Theme design tokens.
- Completed `/`, `/events`, `/events/[slug]`, `/submit`, `/about`, and `/calendar` fully integrating with `lib/api.ts`.
- See `.cursor/plans/frontend_plan.md` for full implementation details, completed changes, and future polish updates.
- `generateMetadata`, sitemap, robots, JSON-LD on event pages (moved to `frontend-seo` task — still pending).

**Day 5 — Deploy + polish + SEO [CURRENT]**
- [ ] `backend-communities-topics`: Add `GET /communities` + `GET /topics` endpoints; wire topic filter to dropdown.
- [ ] `frontend-seo`: `generateMetadata` on `/events/[slug]`, JSON-LD Event schema, `sitemap.ts`, `robots.ts`.
- [ ] `frontend-polish`: SWR filter transitions, Prev/Next pagination, skeleton loading, Vercel Analytics.
- [ ] Verify Alembic migration file exists in `backend/alembic/versions/` (run `make migrate` against clean DB).
- [ ] Vercel deploy for web; VPS deploy for api + worker + beat + postgres + redis + Caddy TLS.
- [ ] Env hardening (rotating JWT secret, Gemini quota check, cron smoke-test).
- [ ] End-to-end smoke run: crawl → event appears → Register Now → ICS feed → submit → moderation → approve.
- [ ] Launch.

## Non-negotiable quality rules (applied throughout)

- `DATABASE_URL` for FastAPI MUST start with `postgresql+asyncpg://`.
- `ALEMBIC_DATABASE_URL` uses sync `postgresql+psycopg2://`. `env.py` uses `async_engine_from_config` for online migrations.
- All SQLAlchemy models use `Mapped[type]` + `mapped_column()`.
- All Celery tasks: idempotent, JSON-serialized, no pickle.
- No `print()` in production code — `structlog` structured JSON logs everywhere.
- Every Gemini call wrapped in try/except with fallback to moderation queue on failure.
- **Register Now → button MUST link to `registration_url` (fallback `canonical_url`) with `target="_blank" rel="noopener noreferrer"`.** This is the core product promise.

## MVP acceptance checklist (reproduce at end of Day 5)

**Infrastructure**
- [ ] `make dev` starts all services without errors.
- [ ] `make migrate` applies cleanly to a fresh DB.
- [ ] `make seed` inserts initial sources.

**Data pipeline**
- [ ] GDG Lucknow crawl runs (manually or via Beat) and produces ≥1 published event.
- [ ] `GET /api/v1/events` returns JSON including that event.
- [ ] `/api/v1/feeds/events.ics` subscribes successfully in Google Calendar.

**Frontend**
- [ ] `/events` and `/events/[slug]` render the real event on Vercel; Register Now opens original page.
- [ ] `/events/[slug]` HTML head has correct OG tags and JSON-LD Event schema.
- [ ] `GET /sitemap.xml` lists published event slugs.

**Admin & moderation**
- [ ] Manual submission → appears in moderation queue → admin approves → event visible publicly.
- [ ] Admin login + source trigger-crawl work against production API.

**Ops**
- [ ] Celery Beat schedules visible in Flower; `make lint` passes (Python ruff + ESLint).
- [ ] `GET /api/v1/communities` and `GET /api/v1/topics` return populated data after first crawl.

## Ongoing sourcing of accurate context

Whenever a library API, SDK signature, or external endpoint is in doubt during implementation:

1. First check Context7 for the relevant library (for example `/googleapis/python-genai` for Gemini SDK calls, `/vercel/next.js` for App Router APIs, `/fastapi/fastapi` for FastAPI patterns).
2. Fall back to web search for platform/API endpoints (Meetup GraphQL schema, Devfolio/Commudle DOM selectors, GDG Community Dev endpoints) — these change without notice.
3. Always prefer the official, latest-version docs over cached training knowledge, since the 2026 Gemini model line and SDK have already superseded what the requirements doc assumes.
