# Flow Trials - Handoff (Next Steps)

## Status
- Backend deployed on Render (FastAPI + psycopg3), Supabase as DB. Health check at `/health`.
- Env essentials: `DATABASE_URL` should use the Supabase pooler host with `?sslmode=require`; `FRONTEND_ORIGINS` includes `https://flowtrials-mvp.vercel.app` plus localhost; frontend points to `https://flowtrials-mvp.onrender.com`.
- AI assist endpoints (plain title/summary/quiz) are live and cached in Postgres.

## Recently Completed: Backend Monolithic Refactor
**Goal:** Consolidate backend into 3 clear monolithic modules with inline dependencies (no scattered helper files).

**What changed:**
- Eliminated helper files (`ctgov_client.py`, `ctgov_normalizer.py`, `embeddings.py`)
- Consolidated backend into 3 self-contained modules:
  - `platform_module.py`: DB connection, health checks, CORS, startup
  - `search_module.py`: Studies CRUD, search/scoring, CT.gov ingestion helpers, embeddings (all inline)
  - `ai_module.py`: Anthropic integration, caching, rate limiting
- Created `scripts/` directory for runnable workflows:
  - `scripts/ingest_ctgov.py` (canonical)
  - `scripts/backfill_embeddings.py`
  - `backend/ingest_ctgov.py` (backwards-compatible stub)
- `main.py` is now 28 lines (just wires modules together)

**Benefits:**
- All logic for a domain lives in one file with clear section headers (CONFIG, TYPES, DEPENDENCIES, REPO, SERVICE, ROUTES)
- No jumping between files to understand a feature
- Scripts import from modules, not scattered helpers

**File structure:**
```
backend/
  main.py (entrypoint)
  platform_module.py
  search_module.py
  ai_module.py
  ingest_ctgov.py (stub)
scripts/
  ingest_ctgov.py (canonical)
  backfill_embeddings.py
  README.md
```

## Next Task: Search Fallback (Keywords -> NLP)
- Current behavior: `POST /search` in `search_module.py` runs keyword-based scoring over all studies.
- Goal: If the keyword search returns zero items, fall back to an NLP-assisted reformulation and rerun the search.
- Proposed approach:
  1) Run the existing `search_studies`. If `len(results) == 0`, trigger fallback.
  2) NLP step: send the original query to Anthropic to extract structured terms (conditions, interventions, demographics, zip hints, synonyms) and return a concise keyword list.
  3) Rerun search using the extracted terms (e.g., set `conditions_include` from extracted conditions and/or replace `query_text` with the cleaned keyword string).
  4) Include a flag in the response (e.g., `nlp_fallback: true`) so the UI can message the user.
- Implementation touchpoints:
  - Add a helper in `ai_module.py` to call Anthropic for query reformulation (reuse `get_anthropic_client` and `ai_rate_limiter`).
  - Insert fallback logic in `search_module.py` after the initial search in the `/search` route handler.
  - Keep pagination consistent; on fallback, return results normally but mark the fallback flag.
