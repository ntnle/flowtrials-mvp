# Flow Trials

Clinical trial discovery and participation platform.

## Docs

- Product overview: [PRODUCT.md](PRODUCT.md)
- Architecture overview: [ARCHITECTURE.md](ARCHITECTURE.md)
- Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Deep dive (data model, flows, reference): [DOC.md](DOC.md)
- Recent implementation notes: [HANDOFF.md](HANDOFF.md)
- Task framework spec: [STUDY_TASK_FRAMEWORK.md](STUDY_TASK_FRAMEWORK.md)

## App Startup

### Prerequisites

- Python 3.8+
- Node.js 18+
- pnpm
- Supabase CLI (local dev)

### Supabase

```bash
supabase start
supabase db reset
```

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

### Frontend (Svelte)

```bash
cd frontend-sv
pnpm install
cp .env.example .env
pnpm dev
```

## Scripts

Run scripts from the repo root:

```bash
python scripts/<name>.py
```

- `scripts/ingest_ctgov.py`: ClinicalTrials.gov ingestion
- `scripts/backfill_embeddings.py`: backfill embeddings for semantic search
