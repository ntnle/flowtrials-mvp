# Flow Trials - Handoff (Next Steps)

## Status
- Backend deployed on Render (FastAPI + psycopg3), Supabase as DB. Health check at `/health`.
- Env essentials: `DATABASE_URL` should use the Supabase pooler host with `?sslmode=require`; `FRONTEND_ORIGINS` includes `https://flowtrials-mvp.vercel.app` plus localhost; frontend points to `https://flowtrials-mvp.onrender.com`.
- AI assist endpoints (plain title/summary/quiz) are live and cached in Postgres.

## Next Task: Search Fallback (Keywords -> NLP)
- Current behavior: `POST /search` in `backend/main.py` runs keyword-based scoring over all studies.
- Goal: If the keyword search returns zero items, fall back to an NLP-assisted reformulation and rerun the search.
- Proposed approach:
  1) Run the existing `search_studies`. If `len(results) == 0`, trigger fallback.
  2) NLP step: send the original query to Anthropic to extract structured terms (conditions, interventions, demographics, zip hints, synonyms) and return a concise keyword list.
  3) Rerun search using the extracted terms (e.g., set `conditions_include` from extracted conditions and/or replace `query_text` with the cleaned keyword string).
  4) Include a flag in the response (e.g., `nlp_fallback: true`) so the UI can message the user.
- Implementation touchpoints:
  - Add a helper in `backend/main.py` to call Anthropic (reuse `get_anthropic_client` and `ai_rate_limiter`).
  - Insert fallback logic after the initial search in `search_studies` or in a wrapper that handles the `/search` request.
  - Keep pagination consistent; on fallback, return results normally but mark the fallback flag.
