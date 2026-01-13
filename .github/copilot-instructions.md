# Flow Trials - Copilot Instructions

## Read First (Project Truth)
- Start from [DOC.md](DOC.md) for architecture + workflows; consult [HANDOFF.md](HANDOFF.md) for current priorities (e.g., “Search fallback”).

## Agent Roles (opt-in by user prompt)
Default role is **DOER** unless the OPERATOR explicitly asks for planning/review.

If the OPERATOR says **"just do it"**, temporarily prioritize completing the request end-to-end even if it spans roles; keep scope limited to the request and resume normal role discipline afterward.

### PLANNER
Convert the OPERATOR’s request into a minimal plan with acceptance criteria + atomic TODOs for a Doer. Do not write code or add scope. Output only the plan.

### DOER
Implement only the Planner’s TODOs exactly. If blocked/unclear, stop and ask; do not guess. Output only what changed + evidence (commands run, key file links).

### LOOKER
Verify the Doer’s work matches the Planner plan + OPERATOR request. No new code or feature ideas. Output pass/fail + precise fix list.

## Architecture Boundaries (non-negotiable)
- Dual-backend: **FastAPI** for search/study/AI ([backend/main.py](backend/main.py)); **Supabase** for auth + user data/RLS ([frontend/src/lib/supabase.js](frontend/src/lib/supabase.js), [supabase/migrations](supabase/migrations)).
- Frontend: Svelte SPA with monolithic route pages; keep state/handlers/UI together in each page ([frontend/src/routes/Home.svelte](frontend/src/routes/Home.svelte)).

## Data/DB Conventions
- `studies.conditions` + `studies.site_zips` are `TEXT[]` and stored lowercased for search ([supabase/migrations/20260111000000_initial_schema.sql](supabase/migrations/20260111000000_initial_schema.sql)).
- `interventions`, `locations`, `contacts` are JSONB.
- Participation requests require integer `study_id` (strings break inserts) and are unique per `(user_id, study_id)` (duplicate => Postgres `23505`).

## AI Generation + Caching
- AI endpoints are in FastAPI; results cached on the `studies` row with `ai_cache_version` + `ai_cached_at`. Bump `AI_CACHE_VERSION` when prompts/model change ([backend/main.py](backend/main.py)).

## Local Dev (expected order)
```bash
supabase start
supabase db reset

cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

cd ../frontend
pnpm install
pnpm dev
```

## Operations
- Ingest CT.gov: `cd backend && pnpm run ingest:ctgov` ([backend/ingest_ctgov.py](backend/ingest_ctgov.py)).
- Frontend calls FastAPI via `VITE_API_BASE` ([frontend/src/lib/api.js](frontend/src/lib/api.js)); auth uses Supabase env vars.
