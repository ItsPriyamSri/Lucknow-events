# Source Adapters

## Adapter interface

Defined in `backend/ingestion/adapters/base.py`:

- `fetch(source) -> list[ScrapedPage]`
- `extract_raw_events(page) -> list[dict]`
- `get_external_id(raw) -> str | None`

Adapters are selected in `backend/ingestion/pipeline.py` by `source.adapter_type` (`gdg`, `generic`, `meetup`, `commudle`, `devfolio`, `unstop`).

Shared Playwright helpers live in `backend/ingestion/adapters/playwright_util.py` (headless render, jitter, link discovery).

---

## GDG (`gdg`)

**File:** `backend/ingestion/adapters/gdg.py`

**Strategy:**

- Prefer chapter/community JSON event feeds when discoverable.
- Fallback: Playwright on chapter listing and event detail pages.

**Trust:** High deterministic parsing; AI only when fields are missing.

---

## Generic HTML (`generic`)

**File:** `backend/ingestion/adapters/generic.py`

**Strategy:**

- Playwright render → visible text (capped) → pipeline may invoke Gemini Extraction Agent for structured fields.

Used for one-off college or community URLs registered as sources.

---

## Meetup (`meetup`) — Phase 3

**File:** `backend/ingestion/adapters/meetup.py`

**Strategy:**

- If `MEETUP_ACCESS_TOKEN` (or source `config_json` bearer) is set: `POST https://api.meetup.com/gql-ext` with a best-effort GraphQL query (schema may change).
- Otherwise: Playwright on Meetup search/listing pages → discover event URLs → per-page extraction.

**Notes:** GraphQL responses vary; Playwright path is the reliable fallback for Lucknow-scoped discovery.

---

## Commudle (`commudle`) — Phase 3

**File:** `backend/ingestion/adapters/commudle.py`

**Strategy:**

- Playwright SPA: listing page → follow event detail links → cleaned text for AI/deterministic merge.

Selectors and routes follow Commudle’s current DOM; may need tuning if the site changes.

---

## Devfolio (`devfolio`) — Phase 3

**File:** `backend/ingestion/adapters/devfolio.py`

**Strategy:**

- Playwright: discover hackathon/event links from listing or org pages → detail pages.
- Optional: intercept GraphQL/XHR responses when present (`page.on("response", ...)`) for richer JSON.

---

## Unstop (`unstop`) — Phase 3

**File:** `backend/ingestion/adapters/unstop.py`

**Strategy:**

- Try public listing API (`/api/opportunity/listing` with Lucknow-style params); parse heuristic JSON shapes (`data`, `opportunities`, etc.).
- Fallback: Playwright crawl of listing + opportunity URLs.

---

## Operational rules (all adapters)

- Respect `robots.txt` before hitting new domains (enforced in pipeline / fetch layer where configured).
- Headless Playwright in Docker: `--no-sandbox`, realistic user agent.
- Random 0.5–2.0s jitter between page loads; exponential backoff (max 3) on failures.
- SHA256 snapshots before processing; unchanged hash skips re-processing for the same URL/source.
