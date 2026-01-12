# Flow Trials

Clinical trial discovery and participation platform.

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
cd frontend
pnpm install
cp .env.example .env
pnpm dev
```
