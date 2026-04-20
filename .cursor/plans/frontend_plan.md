# Frontend Plan & Implementation Status: Lucknow Tech Events

This document tracks the current state of the frontend implementation and the roadmap for future updates, serving as the primary `frontend-plan` for Phase 2 of the MVP.

## 1. Context & Architecture
- **Framework**: Next.js 16 (App Router) with Turbopack.
- **Styling**: Tailwind CSS v4 using PostCSS proxy and CSS-first configuration via `@theme` directive in `globals.css`.
- **Theme**: "Nawab AI" aesthetic (Deep mochas, muted gold `#D48C51` accents, clean sans-serif typography, highly rounded and glassmorphic UI elements).
- **Icons & Structure**: Lucide React for consistent iconography. Mobile-responsive Sidebar layout.
- **Data Fetching**: Axios client `lib/api.ts` making SSR/ISR requests to `process.env.NEXT_PUBLIC_API_URL`.

---

## 2. Completed Implementation (Current State)

We have successfully scaffolded and integrated the core views for the frontend application:

### A. Core Foundation
- [x] Initialized Next.js 16 setup.
- [x] Migrated from Tailwind v3 to Tailwind v4, utilizing CSS variables.
- [x] Implemented global shell layout (`app/layout.tsx`): Desktop Sidebar + Mobile sticky header.
- [x] Bound `axios` and API interfaces resolving to backend via CORS proxy mapping in `next.config.js`.

### B. Pages Implemented
- **`/` (Home)**: Hero section and populated shelves for Featured and This Week's events.
- **`/events` (Listing)**: Search/Filter forms on the left handling query parameters (`is_free`, `topic`, `q`, etc.) side-by-side with an Event Card grid.
- **`/events/[slug]` (Detail)**: Full static/ISR event rendering. Enforces the strict rule of keeping "Register Now \u2192" pointing externally to `registration_url` via strict fallback logic.
- **`/submit` (Event Submission Form)**: Client-side URL extraction form. Gracefully handles 429 Too Many Requests status (SlowAPI) with animated success/error states.
- **`/calendar` (Calendar View)**: Lists events grouped by actual formatted days with links to `.ics` feeds for Google Calendar.
- **`/about` (About Community)**: Readme page explaining the scraper pipeline with open data feed buttons. 

---

## 3. Future Updates (Roadmap & Next Steps)

While the frontend structure is completely operational, the following tasks are necessary for full production polish in Day 4 and Day 5:

### A. Live Data & SWR Enhancements
- [x] **Live SWR integration**: `/events` uses `swr` + `useSearchParams`; checkboxes and selects call `router.replace` (no full document reload); `keepPreviousData` for smooth revalidation.
- [x] **Pagination Controls**: Prev/Next links with `scroll={false}` and query preservation.
- [x] **Placeholder / Skeleton States**: `app/events/loading.tsx` + `EventGridSkeleton`; Suspense wraps `EventsExplorer`.

### B. Polish & SEO
- [x] **Dynamic Metadata**: `generateMetadata` on `/events/[slug]` (OG + Twitter).
- [x] **JSON-LD Structured Data**: `EventJsonLd` on detail pages.
- [x] **Sitemap Generation**: `app/sitemap.ts` (+ static routes).

### C. Missing Backend Hooks
- [x] **Topics & Localities Endpoint**: `GET /api/v1/topics`, `/localities`, `/communities` with counts; filters use dropdowns.

### D. Deployment
- [x] Added `vercel.json` deploy configuration with Mumbai region settings.
- [x] **Vercel Analytics**: Built into the layout previously.
