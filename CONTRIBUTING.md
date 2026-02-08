# Contributing

This repo intentionally consolidates documentation into three canonical files:
- [PRODUCT.md](PRODUCT.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

This file is written for day-to-day engineering work (run locally, where to change things, and what conventions to follow).

## Repo Layout
- `frontend-sv/`: SvelteKit app (UI + Supabase client)
- `backend/`: FastAPI service (search + AI + published reads)
- `supabase/`: migrations, storage/RLS policies, seed
- `scripts/`: local maintenance/ingestion scripts

## Quickstart (Local Development)
Prereqs:
- Python 3.8+
- Node.js 18+
- `pnpm`
- Supabase CLI

1) Start Supabase:
- `supabase start`
- `supabase db reset`

2) Backend (FastAPI):
- `cd backend`
- Create venv + `pip install -r requirements.txt`
- Run: `uvicorn main:app --reload --port 8000`

Backend env:
- Copy `backend/.env.example` → `backend/.env`
- Key vars:
  - `DATABASE_URL` (Supabase pooler URL with `?sslmode=require`)
  - `ANTHROPIC_API_KEY`
  - `FRONTEND_ORIGINS` (comma-separated)

3) Frontend (SvelteKit):
- `cd frontend-sv`
- `pnpm install`
- Run: `pnpm dev`

Frontend env:
- Copy `frontend-sv/.env.example` → `frontend-sv/.env`
- Key vars:
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
  - `VITE_API_BASE` (defaults to `http://localhost:8000`)

## Where To Make Changes
- UI and page logic: `frontend-sv/src/routes/**/+page.svelte`
- Supabase helper layer: `frontend-sv/src/lib/supabase.js`
- FastAPI client wrapper: `frontend-sv/src/lib/api.js`
- FastAPI implementation: `backend/search_module.py`, `backend/ai_module.py`
- DB/RLS/storage: `supabase/migrations/*.sql`

## Project Conventions (Please Follow)
- **Supabase-first mutations**: writes go through Supabase SDK so RLS is authoritative.
- **FastAPI read-only for the frontend**: avoid adding write endpoints unless the backend verifies Supabase JWT and mirrors RLS checks.
- **Monolithic route pages**: prefer keeping state + handlers + UI together in a single `+page.svelte` per route.
- **Minimal abstractions**: add helpers only when there’s clear duplication and benefit.
- **Security**: never bypass RLS assumptions; prefer adding/adjusting policies in migrations.

## Database & Migrations
- All schema/RLS/storage changes should be done via SQL migrations in `supabase/migrations/`.
- Keep migrations small and focused.
- If you add a new table or bucket, include:
  - RLS enablement and policies
  - any required indexes/constraints

## Scripts
Run scripts from the repo root:
- `python scripts/ingest_ctgov.py`
- `python scripts/backfill_embeddings.py`

## AI Features
- AI endpoints should be cache-backed and idempotent where possible.
- Prefer adding new AI outputs as cached columns or tables with clear ownership and RLS considerations.

## Documentation Updates
If you change core flows or architecture boundaries, update:
- [PRODUCT.md](PRODUCT.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Common Troubleshooting
- CORS blocked: check `FRONTEND_ORIGINS` in `backend/.env`.
- DB connection issues in backend: use Supabase pooler host and include `?sslmode=require`.
- Media not appearing: ensure backend study mapping includes `media`.

## AI Agent Notes (Svelte MCP)
If your environment provides Svelte MCP tooling:
- Use `list-sections` first to locate relevant Svelte/SvelteKit docs.
- Use `get-documentation` to fetch the relevant sections.
- Use `svelte-autofixer` before finalizing Svelte edits.
