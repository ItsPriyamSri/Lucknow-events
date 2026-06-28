# Current State — Architecture & System Design

Living reference for how **Lucknow Tech Events** is built today: components, data flows, and the decisions behind them. For onboarding commands, see [developer-help.md](developer-help.md). For product overview, see [README.md](README.md).

*Last aligned with codebase: June 2026*

---

## 1. What This System Is

An **automated tech-events aggregator** for Lucknow, UP. Events are not manually entered — they are discovered, scraped, extracted by AI, scored, and published (or queued for review) by background workers.

| Principle | Decision |
|---|---|
| Curation model | AI-first automation; humans intervene only via moderation |
| Geographic scope | Lucknow offline events + online events from Lucknow-based communities |
| Source of truth | PostgreSQL (`events` table for published data) |
| Write path | Async Celery workers; API is mostly read + admin |
| Read path | FastAPI → Next.js (SSR/ISR + client fetch) |

---

## 2. High-Level Architecture

```mermaid
flowchart TB
    subgraph ingest [Ingestion — Celery Workers]
        Beat[Celery Beat<br/>Asia/Kolkata]
        Discovery[Discovery Agent<br/>Gemini + Google Search]
        Crawl[Crawl Scheduler]
        Pipeline[Ingestion Pipeline<br/>scrape → extract → score → publish]
        SubTask[Submission Processor]
    end

    subgraph data [Data Layer]
        PG[(PostgreSQL 16)]
        Redis[(Redis 7)]
        Snap[(Snapshot Storage<br/>local / R2)]
    end

    subgraph serve [Serving Layer]
        API[FastAPI API<br/>async SQLAlchemy]
        Web[Next.js 16<br/>App Router]
    end

    subgraph external [External]
        Gemini[Google Gemini API]
        Search[Google Search Grounding]
    end

    Beat --> Discovery
    Beat --> Crawl
    Crawl --> Pipeline
    Discovery --> SubTask
    SubTask --> Pipeline
    Pipeline --> Gemini
    Discovery --> Search
    Pipeline --> Snap
    Pipeline --> PG
    Discovery --> PG
    SubTask --> PG

    API --> PG
    Web -->|"/api/v1/*" rewrite| API
    Pipeline --> Redis
    API -.->|task dispatch| Redis
```

### Deployment Topology (Production)

The system is **split across environments** by capability:

| Component | Host | Why |
|---|---|---|
| Frontend (`apps/web`) | **Vercel** (`bom1` region) | Static/SSR Next.js; edge-friendly |
| HTTP API (`backend/api`) | **Render** or Cloud Run | Long-lived Python process; Swagger, health checks |
| Celery worker + beat | **Render VPS** or `docker-compose.prod.yml` | Persistent processes; cannot run on Vercel serverless |
| PostgreSQL | **Neon** (or self-hosted) | Managed async Postgres |
| Redis | **Upstash** (or self-hosted) | Celery broker + result backend |
| Snapshots | Local disk (dev) / **Cloudflare R2** (prod, optional) | Raw HTML snapshots for change detection |

**Design decision:** Vercel hosts only the Next.js app (`vercel.json` → `experimentalServices.web`). The FastAPI backend is a separate deployable (`backend/Dockerfile`, `render.yaml`). This avoids forcing a monolithic serverless Python runtime and keeps long-running Celery off serverless entirely.

---

## 3. Monorepo Layout

```
Lucknow-events/
├── apps/web/           Next.js frontend
├── backend/
│   ├── ai/             Gemini agent wrappers (extraction, classification, moderation)
│   ├── api/            FastAPI app (routers, services, models, schemas)
│   ├── ingestion/      Pipeline orchestration + platform adapters
│   ├── workers/        Celery app, schedules, task modules
│   └── alembic/        Schema migrations
├── docker/             dev + prod Compose files
├── scripts/            Operational scripts (seed_sources.py)
└── data/               Local snapshot storage (gitignored)
```

**Design decision:** Single repo with clear backend/frontend boundary. No shared TypeScript/Python types package — the API contract is implicit via Pydantic schemas and mirrored TypeScript interfaces in `apps/web/lib/`.

---

## 4. Core Data Model

### Entity relationships

```mermaid
erDiagram
    Source ||--o{ RawEvent : produces
    Source ||--o{ CrawlRun : tracks
    RawEvent ||--o| Event : publishes_to
    ManualSubmission }o--|| Source : creates_temporary
    ModerationQueueItem }o--o| RawEvent : references

    Source {
        uuid id PK
        string base_url
        float trust_score
        string status
        jsonb config_json
    }
    RawEvent {
        uuid id PK
        jsonb raw_payload_json
        jsonb ai_extracted_json
        float extraction_confidence
        string pipeline_status
    }
    Event {
        uuid id PK
        string slug UK
        timestamptz start_at
        boolean date_tba
        float publish_score
        tsvector search_vector
    }
    ManualSubmission {
        uuid id PK
        string event_url
        string status
    }
    ModerationQueueItem {
        uuid id PK
        string reason
        string status
    }
```

### Key tables

| Table | Role |
|---|---|
| `sources` | **Living accumulation log** of crawl targets — grows via discovery, submissions, and admin. Not a static seed list. |
| `raw_events` | Intermediate pipeline state: scraped payload, AI extraction output, confidence, status |
| `events` | Published, queryable event records exposed to the public API |
| `manual_submissions` | User- or AI-submitted URLs awaiting/after processing |
| `moderation_queue` | Low-confidence extractions and page-type failures for admin review |
| `crawl_runs` | Per-source crawl audit trail |

### `Source` design decisions

- **`trust_score`** (0.0–1.0) feeds the publish-score threshold — high-trust platforms (GDG, Commudle) get a lower bar to publish.
- **`status`**: `active` | `whitelisted` | `blacklisted` — blacklisted sources are never crawled.
- **`config_json`**: per-source flags (`watchlist`, `always_refresh`, `max_items`, etc.).
- **`crawl_interval_hours`**: per-source cadence; global beat runs every 12h but each source is due independently.

### `Event` design decisions

- **`slug`**: URL-safe unique identifier for public pages (`/events/[slug]`).
- **`date_tba`**: Events published without a confirmed start date; sorted after dated events, excluded from calendar.
- **`expires_at`**: Soft-expiry for past events (set by cleanup task); filtered out of public queries.
- **`search_vector`**: PostgreSQL `TSVECTOR`, maintained by a DB trigger on title/description/community fields.
- **`publish_score` / `relevance_score`**: Persisted at publish time for auditing and admin display.

---

## 5. Ingestion Pipeline

Entry point: `ingestion/pipeline.py` → `run_source_pipeline(source_id)`, dispatched by Celery.

### Pipeline stages

```mermaid
flowchart TD
    A[1. Fetch via adapter] --> B[2. Snapshot + SHA256 hash]
    B --> C{Content unchanged?}
    C -->|yes| Skip[Skip page]
    C -->|no| D[3. Insert/update RawEvent]
    D --> E[4. Deterministic parse]
    E --> F{Page type = detail?}
    F -->|no| MQ1[Moderation queue]
    F -->|yes| G{Needs AI extract?}
    G -->|yes| H[AI Extraction Agent]
    G -->|no| I[Hybrid: AI classify if low confidence]
    H --> J[5. Normalize dates/location/text]
    I --> J
    J --> K[6. Relevance score]
    K --> L[7. Deduplicate]
    L --> M[8. Compute publish score]
    M --> N{score ≥ threshold?}
    N -->|yes| P[Publish Event]
    N -->|borderline| R[Re-classify + retry]
    R --> N
    N -->|no| MQ2[Moderation queue]
    P --> Q[9. Enqueue feed rebuild stub]
```

### Adapter layer

| Adapter | Status | Strategy |
|---|---|---|
| `generic` | **Production** | Playwright render → cleaned text → AI extraction |
| `static` | **Dev/seed** | Hardcoded events for local testing (`scripts/seed_sources.py`) |
| Platform-specific (GDG, Commudle, lu.ma, etc.) | **Planned** | Deterministic parsers before AI fallback |

**Design decision:** Generic adapter uses Playwright (not plain httpx) because most event platforms are JS-rendered SPAs. This trades latency/cost for extraction accuracy.

**Design decision:** Content-hash snapshots (`ingestion/storage.py`) skip unchanged pages unless `config_json.always_refresh` is set. Reduces redundant LLM calls on stable pages.

### Pre-LLM guards

Before any Gemini call, the pipeline applies cheap filters:

1. **Page-type classification** — listing/browse pages go straight to moderation (`url_listing`, `url_unknown`, etc.).
2. **Garbage pre-filter** — short pages, pure JS/CSS soup, 404s, no event vocabulary (in extraction path).
3. **Conditional AI** — deterministic parse first; AI only when confidence < 0.60 or platform is in the generic set.

**Design decision:** Token economy — never send obvious garbage to Gemini. Listing pages from discovery are also blocked by regex (`workers/tasks/discovery.py` `_LISTING_BLOCKLIST`).

### Publish score formula

Weighted composite (`ingestion/publish_score.py`):

| Factor | Weight |
|---|---|
| Source trust score | 0.25 |
| Extraction confidence | 0.20 |
| Location confidence (relevance) | 0.20 |
| Field completeness | 0.15 |
| Relevance score | 0.15 |
| Dedup certainty | 0.05 |

**Dynamic threshold** by source trust:

| Source `trust_score` | Publish threshold |
|---|---|
| ≥ 0.85 | 0.60 |
| ≥ 0.70 | 0.68 |
| < 0.70 | 0.75 |

**Design decision:** Trusted platforms (GDG, established communities) can publish with slightly incomplete data (e.g. missing venue). User submissions and unknown sources face a stricter bar.

### Date TBA path

If extraction finds a strong event but **no start date**, the pipeline may still publish with `date_tba=true` rather than blocking. TBA events:

- Appear at the bottom of the events list
- Are excluded from the calendar view
- Auto-expire after 30 days if no date is ever found
- Get re-checked on subsequent watchlist crawls

**Design decision:** A visible "date TBA" listing is better than hiding events that communities have announced but not yet dated.

### Deduplication

`ingestion/dedup.py`:

1. Exact `canonical_url` match → duplicate
2. Fuzzy: same title (case-insensitive) within ±12h window → duplicate

**Design decision:** Conservative dedup — prefer missing a duplicate over merging distinct events. URL match is authoritative.

### Relevance scoring

`ingestion/relevance.py` scores Lucknow fit (0.0–1.0):

- Offline events: locality/institution keyword matching against curated Lucknow lists
- Online events: organizer/community name matching against known Lucknow tech communities
- Offline outside Lucknow → 0.1 (likely rejected downstream)

---

## 6. AI Agents

All agents use the `google-genai` SDK (`ai/gemini_client.py`) with structured JSON output via Pydantic schemas.

| Agent | Model (typical) | Trigger | Output |
|---|---|---|---|
| **Discovery** | `gemini-2.0-flash` + Google Search | Celery beat (12h) or admin | List of individual event URLs |
| **Extraction** | `GEMINI_MODEL` (default `gemini-3.0-flash`) | Pipeline step 4 | Structured event JSON + confidence |
| **Classification** | Same | Borderline publish scores | Refined event type / flags |
| **Moderation** | Same | Community submission triage | approve / reject / human_review |
| **Submission gate** | Same | Before processing user URLs | Valid tech event? yes/no |

### Discovery agent flow

1. Gemini designs its own search strategy (or admin supplies custom queries)
2. Google Search Grounding returns result text
3. URLs extracted via regex from free-form response
4. Listing-page regex filter applied
5. Each surviving URL → `create_submission()` → unified submission pipeline

**Design decision:** Discovery does not write directly to `sources` or `events`. It funnels through the same submission path as community form submissions, ensuring one validation pipeline for all inbound URLs.

### Mock mode

`AI_MODE=mock` in `.env` returns synthetic agent output without calling Gemini. Used for frontend/admin development without API quota.

**Design decision:** Mock is opt-in (`AI_MODE`), not automatic fallback in production (`AI_FALLBACK_TO_MOCK` exists in config but agents check `AI_MODE` explicitly).

---

## 7. Submission Flow (Community + Discovery)

```mermaid
sequenceDiagram
    participant User as User / Discovery Agent
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Celery as Celery Worker
    participant Pipe as Ingestion Pipeline

    User->>API: POST /submissions (or discovery internal)
    API->>DB: Insert manual_submission (status=queued)
    API->>Celery: process_manual_submission.delay()
    Celery->>Celery: AI gate (is this a tech event?)
    alt rejected
        Celery-->>DB: submission status=rejected
    else accepted
        Celery->>DB: Create temporary Source (watchlist=true)
        Celery->>Pipe: run_source_pipeline(source_id)
        alt published
            Pipe-->>DB: Event created, source stays enabled
        else failed
            Celery-->>DB: Disable/delete source
        end
    end
```

**Design decision:** Successful submissions create a **watchlist source** (`config_json.watchlist=true`) that gets periodically re-crawled (`workers/tasks/watchlist.py`) to catch date announcements and description updates.

**Design decision:** Rate limit on public submissions — `5/hour` per IP (`slowapi` on `POST /submissions`).

---

## 8. Background Jobs (Celery Beat)

Timezone: **Asia/Kolkata**. All schedules in `workers/schedules.py`.

| Task | Schedule | Purpose |
|---|---|---|
| `crawl_all_sources` | Every 12h | Enqueue pipeline for due sources |
| `auto_discover_events` | Every 12h (+30 min offset) | AI URL discovery |
| `refresh_watchlist_sources` | Every 12h (+45 min offset) | Re-scrape single-event watchlist URLs |
| `rebuild_all_feeds` | Every 30 min | **Stub** — feeds are on-demand today |
| `expire_past_events` | Daily 03:00 | Soft-expire and hard-delete junk dates |

Worker concurrency: 8 in dev, 4 in prod Compose.

**Design decision:** Celery Beat and workers must co-locate with Redis and have persistent uptime. They are not deployed to Vercel.

---

## 9. API Layer

### Public routes (`/api/v1`)

| Prefix | Purpose |
|---|---|
| `/events` | List, filter, search, featured, this-week, by slug |
| `/feeds` | `events.json`, `events.ics` (generated on request) |
| `/submissions` | Community event URL submission |
| `/discovery` | Public discovery status endpoints |

### Admin routes (`/api/v1/admin`)

JWT Bearer auth (`api/core/deps.py` → `get_current_admin`). Login via bcrypt-verified `ADMIN_EMAIL` + `ADMIN_PASSWORD_HASH`.

| Prefix | Purpose |
|---|---|
| `/auth` | Login → JWT |
| `/events` | CRUD on live events |
| `/sources` | Manage crawl sources |
| `/moderation` | Review queue items |
| `/discovery` | Trigger discovery runs, submit URLs |
| `/stats` | Dashboard aggregates |

### Database connections

`api/core/database.py`:

| Environment | Pool strategy |
|---|---|
| Docker dev (`DOCKER_ENV=1`) | Standard SQLAlchemy pool with `pool_pre_ping` |
| Cloud (Render/Vercel/Cloud Run) | `NullPool` — new connection per request |

**Design decision:** Serverless and connection-limited cloud Postgres (Neon) cannot sustain a warm connection pool from many ephemeral instances. NullPool trades latency for connection safety.

### Logging & observability

Structured logging is centralized across API, workers, and frontend.

```mermaid
flowchart LR
    subgraph sources [Log sources]
        API[FastAPI middleware]
        Celery[Celery task hooks]
        Pipe[Ingestion pipeline]
        Web[Next.js Pino]
    end

    subgraph context [Shared context]
        RID[request_id / correlation_id]
        TID[task_id]
        SVC[service + environment]
    end

    API --> context
    Celery --> context
    Pipe --> context
    context --> Out[stdout JSON or console]
    Web --> Out
```

| Component | Module | What it logs |
|---|---|---|
| **API** | `api/core/logging.py` | Shared structlog config, contextvars |
| **HTTP** | `api/middleware/request_logging.py` | Every request: method, path, status, `duration_ms`; returns `X-Request-ID` |
| **Workers** | `workers/logging_hooks.py` | Worker startup, task start/finish/failure with duration |
| **Task dispatch** | `workers/dispatch.py` | Propagates `correlation_id` in Celery headers |
| **Pipeline** | `ingestion/pipeline.py` | `pipeline.started/completed`, `event.published`, duplicates, failures |
| **Adapters** | `ingestion/adapters/generic.py` | `adapter.fetch_started/completed/failed` with `duration_ms` |
| **Submissions** | `api/services/submission_service.py` | `submission.created`, `submission.task_queued` |
| **Admin** | `api/routers/admin/auth.py` | `admin.login_success`, `admin.login_failed` |
| **Frontend** | `apps/web/lib/logger.ts` | Pino logger; replaces all `console.*` |

#### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LOG_FORMAT` | `json` | `json` (production) or `console` (local dev) |
| `SERVICE_NAME` | `api` | Tag on every log line (`api`, `worker`, `web`) |
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `NEXT_PUBLIC_LOG_LEVEL` | `debug` in dev | Frontend Pino level |

Docker dev sets `LOG_FORMAT=console` and per-service `SERVICE_NAME` for readable terminal output.

#### Standard log fields

Every backend log line includes (when applicable):

- `timestamp`, `level`, `event` (e.g. `pipeline.published`)
- `service`, `environment`
- `request_id`, `correlation_id` — trace a submission from HTTP → Celery → pipeline
- `task_id`, `task_name` — Celery context
- Domain fields: `source_id`, `platform`, `url`, `duration_ms`, `publish_score`

#### Example log flow (submission)

```
[INFO]  http.request              method=POST path=/api/v1/submissions status=200 duration_ms=45
[INFO]  submission.created        submission_id=... event_url=https://lu.ma/...
[INFO]  submission.task_queued    task_id=... correlation_id=<request_id>
[INFO]  celery.task_started       task_name=process_manual_submission
[INFO]  adapter.fetch_started     platform=generic url=https://lu.ma/...
[INFO]  adapter.fetch_completed   duration_ms=3200
[INFO]  event.published           slug=gdg-meetup publish_score=0.84
[INFO]  celery.task_finished      state=SUCCESS duration_ms=8500
```

#### Querying logs

- **Local:** `docker compose -f docker/docker-compose.dev.yml logs -f api worker`
- **Production:** Pipe Render stdout to a log drain (Axiom, Better Stack, Datadog) — not yet configured

`/health` requests are logged at **debug** to avoid noise from the frontend keep-alive ping (every 30s).

**Design decision:** structlog + contextvars over plain `print()` — enables correlation across async HTTP and Celery without passing IDs through every function signature. Celery child tasks inherit `correlation_id` via `workers/dispatch.enqueue()`.

**Not yet implemented:** centralized log drain, Sentry error tracking, Prometheus metrics, OpenTelemetry traces.

---

## 10. Frontend Architecture

### Stack

- **Next.js 16** App Router, React 19, TypeScript strict
- **Tailwind CSS 4** for styling
- **SWR** for client-side data fetching on interactive pages
- **Axios** API client with environment-aware base URL
- **Pino** (`apps/web/lib/logger.ts`) for structured frontend logging

### API routing pattern

```mermaid
flowchart LR
    Browser["Browser<br/>fetch('/api/v1/events')"]
    Next["Next.js<br/>next.config.js rewrites"]
    API["FastAPI<br/>:8000"]

    Browser --> Next
    Next --> API
```

- **Browser:** always calls relative `/api/v1/*` (same origin, no CORS)
- **SSR/RSC:** uses `INTERNAL_API_URL` (Docker: `http://api:8000/api/v1`) or `NEXT_PUBLIC_API_URL` (production)

**Design decision:** Next.js rewrite proxy hides the backend URL from the browser and eliminates CORS configuration complexity across dev/staging/prod.

### Rendering strategy

| Page | Strategy |
|---|---|
| `/events/[slug]` | SSR with `revalidate = 3600` (ISR, 1h) + `generateMetadata` for SEO |
| `/events` (explorer) | Client component with SWR for filters/pagination |
| `/mission-control` | Client-only admin dashboard |

### Mission Control (admin UI)

- Hidden route: `/mission-control?key=wakandaforever` (secret key gate in component, not middleware)
- JWT stored in `localStorage` as `admin_token`
- Tabs: Events, Sources, Discovery, Queue (pipeline moderation), Community (submissions)
- Not linked from public navigation

**Design decision:** Obscurity gate (`?key=`) is a lightweight access control layer on top of JWT auth — not security-grade, but sufficient to keep the admin UI out of crawlers and casual discovery.

---

## 11. Search & Feeds

### Full-text search

PostgreSQL `TSVECTOR` on `events.search_vector`, updated by a `BEFORE INSERT OR UPDATE` trigger. Queries use `plainto_tsquery` with `ILIKE` fallbacks on title/description/community.

**Design decision:** Postgres-native search avoids Elasticsearch operational overhead at current scale (~60–80 events/year in Lucknow).

### Feeds

`GET /api/v1/feeds/events.json` and `events.ics` are generated **on each request** from live DB queries. The `rebuild_all_feeds` Celery task is a placeholder for future materialized/cached feeds.

---

## 12. Snapshot Storage

| `STORAGE_TYPE` | Backend | Use case |
|---|---|---|
| `local` | Filesystem (`LOCAL_STORAGE_PATH`) | Docker dev |
| `r2` | Cloudflare R2 via boto3 S3 API | Production (optional) |

Snapshots store raw HTML + content-hash sidecar for change detection. Path pattern: `snapshots/{source_id}/{version}:{url_hash}.raw`.

---

## 13. Security Model (Current)

| Concern | Implementation |
|---|---|
| Admin auth | JWT (HS256), bcrypt password hash in env; login success/failure logged |
| Public write | Rate-limited submissions (`5/hour`/IP) |
| CORS | Configurable `CORS_ORIGINS`; mitigated in practice by Next.js proxy |
| Secrets | `.env` only; never committed |
| IDOR | Admin routes require JWT; public routes are read-only except submissions |
| SSRF | Submission URLs processed by worker with Playwright — no internal network guard documented |

**Known gap:** Mission Control secret key is hardcoded in frontend source. Admin JWT has no refresh token rotation.

---

## 14. Key Design Decisions (Summary)

| # | Decision | Rationale | Trade-off |
|---|---|---|---|
| 1 | AI-first, not manual CRUD | Scale without curator bottleneck | Gemini API cost + extraction errors |
| 2 | Unified submission pipeline | One validation path for users, discovery, and admin | Extra indirection vs direct source creation |
| 3 | Weighted publish score + dynamic threshold | Balance automation with quality; trust known platforms | Tuning complexity |
| 4 | Moderation queue, not hard reject | Recoverable human review for borderline extractions | Admin workload |
| 5 | Playwright for generic scraping | JS-heavy event platforms | Slow, resource-heavy crawls |
| 6 | Content-hash skip | Avoid redundant LLM calls | Stale data if page changes without hash collision |
| 7 | Split Vercel + Render deployment | Right runtime for each component | Multi-service ops, env var coordination |
| 8 | NullPool in cloud | Serverless-safe DB connections | Higher per-request DB latency |
| 9 | Next.js API rewrite proxy | No CORS, hidden backend URL | Next.js becomes a required proxy hop |
| 10 | Sources as living log | System learns new URLs over time | Table grows; needs blacklist/expire hygiene |
| 11 | Watchlist re-crawl | Catch date TBA → dated transitions | Ongoing crawl cost for each submission |
| 12 | Postgres TSVECTOR search | Simple ops at low volume | Limited search quality vs dedicated engine |
| 13 | `date_tba` publish path | Surface announced-but-undated events | Calendar pollution risk (mitigated by exclusion) |
| 14 | Mock AI mode | Dev without API key | Divergence from production behavior |
| 15 | Centralized structlog + correlation IDs | Trace async flows API → Celery → pipeline | Needs prod log drain for searchability |

---

## 15. Known Limitations & WIP

| Area | Current state |
|---|---|
| Platform adapters | Only `generic` + `static`; GDG/Commudle/lu.ma parsers not built |
| Feed rebuild | Celery task is a stub; feeds served on-demand |
| Batch extraction | One LLM call per URL (no batching) |
| Discovery memory | No persistent learning of which search strategies work |
| Tests | `pyproject.toml` configures pytest; no test suite in repo yet |
| R2 storage | Implemented but optional; most dev uses local disk |
| Community submission moderation UI | Exists in Mission Control; full auto-publish flow partially wired |
| Observability drain | Logs go to stdout only; no Axiom/Datadog/Sentry wired yet |
| `experimentalServices` in root `vercel.json` | May not reflect actual production split (frontend-only on Vercel today) |

---

## 16. Environment Matrix

| Variable | Dev (Docker) | Production |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@postgres:5432/...` | Neon async URL |
| `REDIS_URL` | `redis://redis:6379/0` | Upstash `rediss://...` |
| `INTERNAL_API_URL` | `http://api:8000/api/v1` (web container) | N/A (Vercel uses `NEXT_PUBLIC_API_URL`) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Cloud Run/Render URL |
| `DOCKER_ENV` | `1` | unset |
| `GEMINI_API_KEY` | Required (or `AI_MODE=mock`) | Required |
| `STORAGE_TYPE` | `local` | `local` or `r2` |
| `LOG_LEVEL` | `INFO` | `INFO` (use `WARNING` in prod if noisy) |
| `LOG_FORMAT` | `console` (Docker dev) | `json` |
| `SERVICE_NAME` | `api` / `worker` | per-service tag |
| `ENVIRONMENT` | `development` | `production` |
| `NEXT_PUBLIC_LOG_LEVEL` | `debug` | `info` |

---

## 17. Request Lifecycle (Read Path)

```mermaid
sequenceDiagram
    participant U as User Browser
    participant N as Next.js
    participant A as FastAPI
    participant D as PostgreSQL

    U->>N: GET /events/some-slug
    N->>A: GET /api/v1/events/some-slug (SSR, INTERNAL_API_URL)
    A->>D: SELECT event WHERE slug=...
    D-->>A: Event row
    A-->>N: EventDetailResponse JSON
    N-->>U: HTML + metadata + JSON-LD
```

Public list/filter requests from the events explorer follow the same proxy path but originate client-side via SWR.

---

*This document reflects the codebase as-is. Update it when architecture changes — especially deployment topology, pipeline thresholds, and adapter additions.*
