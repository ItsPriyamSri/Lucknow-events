# Developer Help Guide

Onboarding guide for contributors to **Lucknow Tech Events** — an AI-powered aggregator of tech events in Lucknow, UP. For a high-level product overview, see [README.md](README.md). This document focuses on getting the stack running locally, understanding how code is organized, and making your first contribution.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) or [Podman](https://podman.io/) | Compose plugin required | Recommended path — runs the full stack |
| [Node.js](https://nodejs.org/) | 20+ | Only if running the frontend outside Docker |
| [pnpm](https://pnpm.io/) | latest | `npm i -g pnpm` |
| [Google Gemini API key](https://aistudio.google.com/app/apikey) | — | Required for real AI discovery/extraction (optional in mock mode) |

---

## First-Time Setup

### 1. Clone the repository

```bash
git clone https://github.com/ItsPriyamSri/Lucknow-events.git
cd Lucknow-events
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

- **`GEMINI_API_KEY`** — your Google AI Studio key (skip if using mock mode below)
- **`JWT_SECRET`** — any long random string (e.g. `openssl rand -hex 32`)
- **`ADMIN_PASSWORD_HASH`** — bcrypt hash of your chosen admin password (see below)
- **`ADMIN_EMAIL`** — defaults to `admin@example.com`; change if you like

**Generate an admin password hash** (after the stack is running):

```bash
docker compose -f docker/docker-compose.dev.yml exec api python -c \
  "from api.core.security import hash_password; print(hash_password('your-password-here'))"
```

Paste the output into `ADMIN_PASSWORD_HASH` in `.env`, then restart the `api` service.

> **Local Docker hostnames:** `.env.example` uses Docker service names (`postgres`, `redis`, `api`). Keep these when running via Compose. Do not point `DATABASE_URL` / `REDIS_URL` at production Neon/Upstash URLs unless you intend to hit remote infra from local containers.

### 3. Start the stack

```bash
# Option A — Makefile shortcut
make dev

# Option B — explicit compose
docker compose -f docker/docker-compose.dev.yml up --build
```

| Service | URL |
|---|---|
| Frontend (Next.js) | http://localhost:3000 |
| Backend API (FastAPI) | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Celery monitor (Flower) | http://localhost:5555 |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

### 4. Run database migrations

In a second terminal:

```bash
make migrate
# or: docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head
```

### 5. Seed demo data (optional, no AI required)

Loads a static test source with sample events so you can explore the UI immediately:

```bash
make seed
```

### 6. Verify everything works

- Open http://localhost:3000 — events list should load (may be empty until seeded or discovered)
- Open http://localhost:8000/health — should return `{"ok": true}`
- Open http://localhost:8000/docs — interactive API reference

---

## Environment Variables Reference

Copy from `.env.example`. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+asyncpg://…`) |
| `ALEMBIC_DATABASE_URL` | Sync URL for Alembic (`postgresql+psycopg2://…`) |
| `REDIS_URL` | Celery broker + result backend |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GEMINI_MODEL` | Default: `gemini-3.0-flash` |
| `AI_MODE` | `gemini` (default) or `mock` — mock skips real LLM calls for local UI/dev work |
| `JWT_SECRET` | Signs admin JWT tokens |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD_HASH` | Mission Control login credentials |
| `NEXT_PUBLIC_API_URL` | Browser-visible API base (`http://localhost:8000/api/v1`) |
| `INTERNAL_API_URL` | Server-side API base inside Docker (`http://api:8000/api/v1`; set automatically by compose for `web`) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `STORAGE_TYPE` / `LOCAL_STORAGE_PATH` | Snapshot storage (`local` + `/app/data/snapshots` in dev) |

**Mock mode (no Gemini key):** add `AI_MODE=mock` to `.env`. Extraction and classification agents return synthetic data; useful for frontend and admin UI work without API quota.

---

## Project Structure

```
Lucknow-events/
├── apps/web/                 # Next.js 16 frontend (App Router, TypeScript, Tailwind)
│   ├── app/                  # Pages and routes
│   ├── components/           # Shared UI
│   └── lib/                  # API clients (api.ts, admin-api.ts)
├── backend/
│   ├── ai/                   # Gemini agents (extraction, classification, moderation)
│   ├── api/                  # FastAPI application
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── routers/          # HTTP route handlers
│   │   ├── schemas/          # Pydantic request/response models
│   │   └── services/         # Business logic
│   ├── ingestion/            # Scraping adapters + pipeline orchestration
│   ├── workers/              # Celery tasks and beat schedules
│   └── alembic/              # Database migrations
├── docker/
│   ├── docker-compose.dev.yml   # Local development (hot reload)
│   └── docker-compose.prod.yml  # Self-hosted production stack
├── scripts/                  # One-off utilities (e.g. seed_sources.py)
├── data/                     # Local scraped snapshots (gitignored)
├── Makefile                  # Common dev commands
└── .env                      # Local secrets (gitignored)
```

### Where to start for common tasks

| Task | Start here |
|---|---|
| Public events UI | `apps/web/app/events/` |
| Event detail page | `apps/web/app/events/[slug]/page.tsx` |
| Community submit form | `apps/web/components/CommunitySubmitForm.tsx` |
| Public API endpoints | `backend/api/routers/events.py`, `submissions.py` |
| Admin API | `backend/api/routers/admin/` |
| Ingestion logic | `backend/ingestion/pipeline.py` |
| AI extraction | `backend/ai/extraction_agent.py` |
| Scheduled background jobs | `backend/workers/schedules.py` |
| DB schema changes | `backend/api/models/` → Alembic migration |

---

## How the Platform Works

This is **not** a typical manual CRUD app. Events are discovered, scraped, extracted, scored, and published (or queued for review) automatically.

```
Discovery Agent (Gemini + Google Search)
        │ individual event URLs
        ▼
Ingestion Pipeline (scrape → pre-filter → extract → score → publish/moderate)
        │ structured Event records
        ▼
PostgreSQL  ←→  FastAPI  ←→  Next.js
```

### Background schedules (Celery Beat, Asia/Kolkata)

| Task | Interval | File |
|---|---|---|
| Crawl all enabled sources | Every 12 hours | `workers/tasks/crawl.py` |
| AI event discovery | Every 12 hours (offset +30 min) | `workers/tasks/discovery.py` |
| Refresh watchlist sources | Every 12 hours (offset +45 min) | `workers/tasks/watchlist.py` |
| Rebuild JSON/ICS feeds | Every 30 minutes | `workers/tasks/feeds.py` |
| Expire past events | Daily at 03:00 | `workers/tasks/crawl.py` |

### Ingestion pipeline (per URL)

1. **Fetch** page HTML via adapter (`ingestion/adapters/`)
2. **Pre-filter** garbage (404s, JS-only shells, no event signal) to save LLM tokens
3. **Extract** structured JSON with Gemini (`ai/extraction_agent.py`)
4. **Normalize** dates, locations, and text
5. **Score** relevance and compute a composite **publish score** (`ingestion/publish_score.py`)
6. **Decide:** publish immediately, publish as **Date TBA**, or send to **moderation queue**

Publish thresholds are **dynamic** based on source trust:

| Source trust | Publish threshold |
|---|---|
| ≥ 0.85 (high-trust platforms) | 0.60 |
| ≥ 0.70 | 0.68 |
| Otherwise | 0.75 |

Events missing a start date but otherwise strong may publish with `date_tba=true` (shown at the bottom of the list, excluded from calendar). Low-confidence extractions land in the moderation queue for admin review.

### API routing (frontend → backend)

The browser calls `/api/v1/*` on the Next.js origin. `apps/web/next.config.js` rewrites those requests to the FastAPI backend — in Docker this targets `http://api:8000`, avoiding CORS issues.

---

## Daily Developer Commands

### Makefile shortcuts

```bash
make dev        # Start full dev stack
make down       # Stop stack and remove volumes
make migrate    # Apply Alembic migrations
make seed       # Seed static demo sources/events
make logs       # Tail api + worker logs
make shell      # Bash into api container
make lint       # Ruff check + format check (backend)
make format     # Auto-format backend with Ruff
make crawl-all  # Manually trigger crawl of all sources
```

### Trigger AI discovery manually

```bash
docker compose -f docker/docker-compose.dev.yml exec api python -c \
  "from workers.tasks.discovery import auto_discover_events; auto_discover_events.delay(); print('Discovery queued.')"
```

Or use **Mission Control → Discovery tab** (requires admin login).

### Run individual services

```bash
# API + DB + Redis only (no frontend workers)
docker compose -f docker/docker-compose.dev.yml up api postgres redis

# Frontend only (host machine — API must be reachable at localhost:8000)
cd apps/web && pnpm install && pnpm dev

# Celery worker / beat only
docker compose -f docker/docker-compose.dev.yml up worker
docker compose -f docker/docker-compose.dev.yml up beat
```

### Database migrations

```bash
# Apply all pending
docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head

# Create a new migration after model changes
docker compose -f docker/docker-compose.dev.yml exec api \
  alembic revision --autogenerate -m "describe_your_change"

# Roll back one step
docker compose -f docker/docker-compose.dev.yml exec api alembic downgrade -1
```

### Linting and formatting

```bash
# Backend (inside Docker)
make lint && make format

# Frontend (on host)
cd apps/web && pnpm lint
cd apps/web && pnpm format:write
```

---

## Mission Control (Admin Dashboard)

Hidden admin UI for reviewing AI output and managing the platform. Not linked from the public site.

| | |
|---|---|
| **URL** | http://localhost:3000/mission-control?key=wakandaforever |
| **Login** | Email/password from `ADMIN_EMAIL` / your `ADMIN_PASSWORD_HASH` |

Wrong `?key=` shows a fake 404. After login, a JWT is stored in `localStorage` as `admin_token`.

### Tabs

| Tab | Purpose |
|---|---|
| **Events** | View, edit, and delete live events |
| **Sources** | Manage crawl sources (enable/disable, trust scores) |
| **Discovery** | Trigger AI discovery runs (default or custom queries) |
| **Queue** | Review low-confidence extractions from the pipeline |
| **Community** | Review user-submitted event links |

Admin API routes live under `/api/v1/admin/*` and require a Bearer token from `POST /api/v1/admin/auth/login`.

---

## Contributing

### Workflow

1. Fork the repo and create a branch: `git checkout -b feat/short-description`
2. Make changes following existing patterns in the touched area
3. Run migrations if you changed ORM models
4. Test locally with `make dev` (or targeted service commands above)
5. Run linters (`make lint`, `pnpm lint` in `apps/web`)
6. Open a pull request with a clear description of **what** changed and **why**

### Code conventions

| Area | Convention |
|---|---|
| **Backend** | Python 3.12, `async/await`, type hints, PEP 8 via Ruff |
| **Frontend** | TypeScript strict mode, functional React components, Tailwind utility classes |
| **Commits** | Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, etc.) |
| **Secrets** | Never commit `.env` or API keys — use `.env.example` for documentation only |
| **Migrations** | Always autogenerate from model changes; review the generated SQL before committing |

### Suggested first contributions

- Platform-specific source adapters in `backend/ingestion/adapters/` (GDG, Commudle, lu.ma, etc.)
- UI polish on `apps/web/app/events/`
- Tests in `backend/tests/` (directory scaffolded via `pyproject.toml`; `make test` runs pytest when tests exist)
- Improving extraction prompts in `backend/ai/`

---

## Production vs Local (Gotchas)

### Split deployment

Production uses a **split architecture**:

- **Frontend** → [Vercel](https://vercel.com) (`apps/web`, region `bom1`)
- **API** → [Render](https://render.com) or Cloud Run (`backend/Dockerfile`, see `render.yaml`)
- **Workers** → Must run on a persistent host (Render, VPS, or `docker-compose.prod.yml`) — **not** on Vercel

Vercel's `vercel.json` only hosts the Next.js app. The FastAPI backend is a separate service. Set `NEXT_PUBLIC_API_URL` in Vercel to your Render/Cloud Run API URL so Next.js rewrites proxy correctly.

### Celery on serverless

Celery workers and Beat **cannot** run on Vercel's serverless runtime. In production you need:

- A running `worker` + `beat` process (see `docker/docker-compose.prod.yml`)
- Managed PostgreSQL (e.g. Neon) and Redis (e.g. Upstash) with URLs in env vars

Trigger discovery manually via Mission Control or `POST /api/v1/admin/discovery/run` (admin JWT required) if Beat is not running.

### Database connection pooling

- **Local Docker:** `DOCKER_ENV=1` enables normal SQLAlchemy connection pooling
- **Cloud (Render/Vercel/Cloud Run):** uses `NullPool` to avoid exhausting serverless connection limits

### bcrypt hash in Docker Compose

When setting `ADMIN_PASSWORD_HASH` in production env files consumed by Compose, bcrypt hashes contain `$` characters. In some shells/compose files you may need to escape them as `$$` — Render's dashboard accepts the hash directly as `$2b$12$...`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Admin login fails | Missing or wrong `ADMIN_PASSWORD_HASH` | Regenerate hash (see setup step 2), restart `api` |
| Frontend can't reach API | `INTERNAL_API_URL` not set in Docker | Compose sets it for `web`; for host-only frontend, ensure API is on `:8000` |
| Discovery does nothing | No `GEMINI_API_KEY` or worker not running | Set key or use `AI_MODE=mock`; check `docker compose … up worker beat` |
| Empty events list | No seed, no discovery run yet | `make seed` or trigger discovery manually |
| Migrations fail | DB not ready | Wait for postgres health, retry `make migrate` |
| Playwright/scrape errors in worker | Chromium not installed | Rebuild backend image: `docker compose … up --build worker` |

Check worker logs: `make logs` or Flower at http://localhost:5555.

---

*Questions? Open a GitHub issue or ask in your PR. Built with ❤️ in Lucknow.*
