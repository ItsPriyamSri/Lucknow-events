# Testing: end-to-end flow (scraper → AI → UI)

This doc is the **step-by-step checklist** to verify the system works end-to-end in dev.

## Preconditions

- Docker Compose works on your machine (Docker or Podman Compose shim).
- You have a local `.env` at repo root (see `.env.example`).

Notes:
- If your `.env` contains bcrypt hashes (values starting with `$2b$...`), Compose may try to interpolate `$VAR` inside them. If you see warnings like `The "QNmLu" variable is not set`, escape `$` as `$$` in that value.

## 1) Boot the dev stack

From repo root:

```bash
docker compose -f docker/docker-compose.dev.yml up --build -d
docker compose -f docker/docker-compose.dev.yml ps
```

Expected:
- `postgres`, `redis`, `api`, `worker`, `beat`, `web` are **Up**
- API available at `http://localhost:8000`
- Web available at `http://localhost:3000`

Quick health check:

```bash
curl -sS http://localhost:8000/health
```

Expected:
- `{"ok":true}`

## 2) Run migrations

```bash
make migrate
```

Expected:
- Alembic runs without errors.

## 3) Seed sources

```bash
make seed
```

Expected:
- Inserts initial sources if missing.
- Includes **`Static Test Source (dev)`** (a deterministic dev-only source that publishes a demo event so you can validate UI wiring even if external sources/AI quotas are failing).

## 4) Trigger crawl (scraper → pipeline)

```bash
make crawl-all
docker compose -f docker/docker-compose.dev.yml logs --tail=200 worker
```

Expected:
- Worker receives `workers.tasks.crawl.crawl_all_sources`
- It dispatches `workers.tasks.pipeline.run_pipeline_for_source` for enabled sources
- At least one source publishes an event

## 5) Verify backend output (pipeline → API)

List events:

```bash
curl -sS http://localhost:8000/api/v1/events
```

Expected:
- JSON response with `total >= 1` once the pipeline has published events.

Also verify detail endpoint works:

```bash
curl -sS http://localhost:8000/api/v1/events/lucknow-tech-events-demo-meetup
```

Expected:
- The event JSON (title, start/end, register URL, etc.)

## 6) Verify UI (API → display)

Open:
- Home: `http://localhost:3000`
- Events list: `http://localhost:3000/events`
- Event detail: `http://localhost:3000/events/lucknow-tech-events-demo-meetup`

Expected:
- The demo event appears in `/events`.
- Clicking into the event shows details.
- The primary CTA opens `registration_url` (new tab) with `rel="noopener noreferrer"`.

## 7) User submitted event link flow (submit → scrape → AI → publish)

Submit a link:

```bash
curl -sS -X POST http://localhost:8000/api/v1/submissions \
  -H 'Content-Type: application/json' \
  -d '{"event_url":"https://example.com/some-event-page","submitter_name":"Test User","submitter_email":"test@example.com"}'
```

Expected:
- Response with an `id` and `status="queued"`
- Worker will pick up `workers.tasks.submissions.process_manual_submission`
- If the page is a real tech event and AI extraction succeeds, the event becomes visible on `/events`
- In that accepted case, the URL is also saved as a new `Source` for future hourly crawls

## 7) AI agent verification (best-effort)

The ingestion pipeline will call the Gemini extraction/classification agents when deterministic parsing confidence is low.

If you see worker logs like:
- `pipeline.ai_extract_failed` / `pipeline.ai_classify_failed`
- HTTP 429 `RESOURCE_EXHAUSTED` (quota / rate limit)

That indicates the AI integration path is wired, but **your API key/project quota currently blocks successful calls**. The system should:
- keep the pipeline running (no crash loop)
- fall back to partial deterministic extraction
- route low-confidence items to moderation when appropriate

## Known external fragility (may be out of our control)

- **GDG**: `https://gdg.community.dev/api/event/...` may return **403** in some environments; HTML fallback may not contain structured event data.
- **Unstop**: their listing API may intermittently return **500**.
- **Gemini**: `429 RESOURCE_EXHAUSTED` means your key/project has no available quota; fix in Google AI Studio / Cloud project billing & quotas.

