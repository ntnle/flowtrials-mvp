# Frontend (SvelteKit)

This repo’s canonical dev setup lives in the root README:
- [CONTRIBUTING.md](../CONTRIBUTING.md)

Quickstart (from this directory):

```bash
pnpm install
pnpm dev
```

## Auth + Supabase Singleton (Important)
- Use the shared Supabase client from `src/lib/supabase.js`.
- Use the shared auth stores from `src/lib/authStore.js`.
- Do not instantiate additional Supabase clients (duplicate GoTrue clients can break auth across the app).

## Tests
This project uses Playwright for E2E tests.

Run from this directory:

```bash
pnpm test:e2e
```

Alias:

```bash
pnpm test
```
