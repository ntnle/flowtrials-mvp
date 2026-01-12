# Flow Trials

## What We Are Building

Flow Trials is a clinical trial discovery and participation platform. Users search and explore studies, then participate in studies they are interested in. The stack splits responsibilities between a FastAPI backend for search and a Supabase backend for auth and user data.

## Architecture Overview

- **Frontend**: Svelte SPA with monolithic route pages in `frontend/src/routes`.
- **Search and study data**: FastAPI (`backend/main.py`) with custom scoring.
- **Auth and user data**: Supabase Postgres (profiles, participation requests).

## Monolithic Page Philosophy

We use monolithic route pages to keep UI logic, data loading, and event handlers together. The goal is to prevent feature logic from being split across many files and to make each page readable in one place.

- Keep forms, lists, and modal UI inline in the page file.
- Share only minimal UI primitives (Card, Input).
- Accept some duplication to keep traceability high.
- Do not extract shared components unless explicitly directed or the page becomes unwieldy.

### Page Responsibilities

- `Home.svelte`: Landing page with search and suggested conditions.
- `Browse.svelte`: Search results and study cards.
- `StudyPage.svelte`: Full study details and participation request entry.
- `Signup.svelte`: Account creation.
- `Login.svelte`: Login form.
- `Profile.svelte`: Profile editor and participation requests.

## Participation Flow

1. **Browse/Search**: User searches via FastAPI and opens a study (`StudyPage.svelte`).
2. **Participate**: Clicking "Participate" checks auth.
3. **If logged out**: Redirect to `Signup.svelte` with a `redirect` query param.
4. **Signup**: Creates the user, migrates anonymous data, then returns to the study page with `fromSignup=true`.
5. **Confirm request**: The study page opens a confirmation modal and inserts a `participation_requests` row with status `pending`.
6. **Post-submit**: User is redirected to `Profile.svelte`, which lists their requests and allows withdrawal (status becomes `withdrawn`).

Participation helpers live in `frontend/src/lib/supabase.js`.

## Supabase Data Model

- `studies`: Clinical trial data (ingested via FastAPI tools).
- `user_profiles`: Extended profile data (10-section form).
- `participation_requests`: User interest in studies.
## Developer Pitfalls

- **Two backends, two responsibilities**: Search stays in FastAPI; auth and user data go through Supabase. Avoid routing everything through FastAPI.
- **Supabase must be running**: Local dev requires `supabase start` plus `supabase db reset` to apply migrations and seed data.
- **Env vars are mandatory**: Configure `backend/.env` and `frontend/.env` from the provided examples or the app will silently fall back to defaults.
- **RLS applies to user tables**: Participation requests and profiles require an authenticated user.
- **Study IDs are integers**: Participation requests expect an integer `study_id`. Passing a string will break inserts.
- **Duplicate participation requests**: The database enforces one request per user per study; Supabase returns error `23505`.

## Local Setup Notes

- Backend env: `backend/.env` (copy from `backend/.env.example`).
- Frontend env: `frontend/.env` (copy from `frontend/.env.example`).
- Supabase local URLs and anon key come from `supabase status`.

## Ingestion Notes

The ingestion script runs in `backend/ingest_ctgov.py` and loads recruiting studies by default. This is intentionally kept in FastAPI because the search scoring and ingestion logic are custom.
