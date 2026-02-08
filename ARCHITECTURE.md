# Flow Trials — Architecture

## At A Glance
Three-tier system with a strict responsibility split:
- **Frontend**: SvelteKit app in `frontend-sv/` (browser client)
- **Backend**: FastAPI service in `backend/` (search + AI + published reads)
- **Data layer**: Supabase (Postgres + Auth + Storage + RLS)

Design constraint: **writes are Supabase-first** so RLS remains the source of truth.

## Hard Boundaries (Agents Should Preserve)
- **All mutations** (INSERT/UPDATE/DELETE, Storage uploads/deletes) happen via **Supabase SDK** from the frontend.
- FastAPI is **read-only for the frontend**: search, AI generation (cache-backed), and published reads.
- Svelte routes are **monolithic**: keep state + handlers + UI in a single `+page.svelte` per route.

## Where To Implement Changes
- UI/UX, routing, forms: `frontend-sv/src/routes/**/+page.svelte`
- Supabase access helpers: `frontend-sv/src/lib/supabase.js`
- FastAPI client wrapper: `frontend-sv/src/lib/api.js`
- FastAPI endpoints: `backend/search_module.py`, `backend/ai_module.py`
- Schema/RLS/storage changes: `supabase/migrations/*.sql`

## Backend API Surface (Frontend-Facing)
- `GET /health`
- `POST /search`
- `GET /studies/{id}` (published reads)
- `POST /ai/plain-title`
- `POST /ai/study-summary`
- `POST /ai/eligibility-quiz`

## Data + Storage Model (What Lives Where)

Postgres tables (selected):
- `studies`: includes `tasks` JSON (task definitions, including media blocks) and cached AI fields
- `participation_requests`: includes `status` and `consent_acknowledged_at` gating
- `task_submissions`: one submission per user per task per study
  - survey answers + audio metadata stored in `task_submissions.responses` (JSONB)

Storage buckets:
- `study-media` (public): recruitment materials
  - path: `{study_id}/{timestamp}_{filename}`
- `study-recordings` (private): participant audio recordings
  - path: `{study_id}/{participation_request_id}/{timestamp}.webm`
  - metadata stored in `task_submissions.responses` as `{path, size, mimeType, uploadedAt}`
- `task-media` (private): researcher-uploaded images/PDFs embedded in tasks
  - path: `{study_id}/{task_id}/{timestamp}_{filename}`

## Security Model (RLS-First)
- Browser clients use Supabase SDK; Postgres RLS and Storage bucket policies decide access.
- Task access gating: must be `approved` and have `consent_acknowledged_at`.
- Private media is accessed via signed URLs.

FastAPI DB connectivity note: use the Supabase pooler host and include `?sslmode=require`.

## Common Agent Mistakes To Avoid
- **Adding FastAPI write endpoints for core mutations**: keep frontend writes Supabase-first so RLS remains authoritative.
- **Writing to Supabase outside RLS expectations**: don’t “work around” RLS by changing clients/roles; fix policies via `supabase/migrations/*.sql`.
- **Breaking task access gating**: tasks and private media must remain gated to `approved` + `consent_acknowledged_at`.
- **Splitting route pages into component sprawl**: prefer monolithic `+page.svelte` files per route; extract only when clearly necessary.
- **Moving task definitions out of `studies.tasks`**: tasks live on the study as JSON; submissions live in `task_submissions`.
- **Storing private file URLs directly**: store Storage paths + metadata; fetch via signed URLs when needed.

## Local Development
- Supabase: `supabase start` then `supabase db reset`
- Backend: `uvicorn main:app --reload --port 8000`
- Frontend: `pnpm dev` in `frontend-sv/`

Details (env vars, scripts, troubleshooting): [CONTRIBUTING.md](CONTRIBUTING.md).
