# E2E Tests (Playwright)

## What these cover (minimal)
- `auth.signup.profile.test.js`: verifies a brand new user can sign up and save their profile.
- `auth.login.seeded.test.js`: verifies an existing seeded researcher can log in.

## Prereqs
- Local Supabase is running.
- No `supabase db reset` is required for these tests.

### Seeded researcher account (one-time)
These tests expect this account to already exist in your local Supabase:
- Email: `test@research.edu`
- Password: `pass123`

You can create it once via the app UI at `/signup`.

## Run
From `frontend-sv/`:
- `pnpm test` (alias for `pnpm test:e2e`)

Notes:
- Playwright builds + previews the app and runs tests against the preview server (see `playwright.config.js`).
