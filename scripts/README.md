# Scripts

This directory contains local-only notebook-style scripts for data ingestion and maintenance tasks.

## Usage

Run scripts directly from the repo root:

```bash
python scripts/<name>.py
```

## Available Scripts

- `ingest_ctgov.py`: ClinicalTrials.gov study ingestion (supports custom conditions via CLI args)
- `backfill_embeddings.py`: Backfill embeddings for semantic search (supports --dry-run, --verify)
