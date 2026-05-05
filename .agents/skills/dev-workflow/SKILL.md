---
name: dev-workflow
description: How to set up, lint, test, build, and run the compliance-reviewer monorepo (FastAPI backend + Next.js frontend + Postgres/pgvector). Use whenever working on this repo.
---

# Compliance Reviewer dev workflow

This repo is a small monorepo with two halves:

- `backend/` — FastAPI service, Python 3.11+, SQLAlchemy 2.0, Alembic, pgvector.
- `frontend/` — Next.js 14 (App Router) + TypeScript + Tailwind.

A `docker-compose.yml` at the repo root spins up Postgres 16 with the `pgvector` extension.

## One-time setup

```bash
pyenv install -s 3.11.11

cd backend
PYENV_VERSION=3.11.11 python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

cd ../frontend
npm install
```

## Lint, type check, and tests

Verified-passing commands as of the initial scaffold commit:

```bash
# backend
cd backend && source .venv/bin/activate
ruff check .
pytest

# frontend
cd frontend
npm run lint        # next lint
npm run typecheck   # tsc --noEmit
npm run build       # next build (also catches type errors)
```

There is no CI configured yet. Run the commands above locally before opening a PR.

## Run the app locally

```bash
# 1. Postgres + pgvector
cp .env.example .env   # only needed once
docker compose up -d

# 2. Backend
cd backend && source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload   # http://localhost:8000, Swagger at /docs

# 3. Frontend
cd frontend
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev                     # http://localhost:3000
```

A full review needs either `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (and `LLM_PROVIDER=openai|anthropic`) plus `OPENAI_API_KEY` for embeddings (only OpenAI embeddings are wired up today).

## Privacy invariants — DO NOT REGRESS

These are encoded in the codebase (`app/logging_setup.py`, `app/services/pipeline.py`, `app/services/storage.py`, `.gitignore`) and must hold for every change:

- **Never commit user documents.** `.env`, `uploads/`, `storage/`, `tmp/`, and any `*.pdf` / `*.docx` / `*.txt` (outside `docs/`) are git-ignored. Don't `git add -f` them.
- **Never log document or prompt contents.** Use `logger.info("…", extra={"contains_document": True})` (or `contains_prompt=True`) for any log line that would otherwise carry user content; the filter drops them.
- **Never store the full source document in the database.** The schema stores only derived data (extracted requirement text, chunked passages). When `DELETE_SOURCE_FILES_AFTER_PROCESSING=true` (default), the pipeline deletes the file, the requirement rows, and the chunk rows after the report is generated.
- **Auth required for upload.** The `POST /uploads` endpoint depends on `get_current_user`; do not add anonymous ingestion paths.
- **No training opt-in.** Do not add code paths that opt providers into training on user content. This is primarily an account-side setting; keep it that way.

## Project structure quick map

```
backend/app/
├── main.py              # FastAPI app, CORS, /healthz, /disclaimer
├── config.py            # Settings via pydantic-settings
├── llm/                 # LLMProvider/EmbeddingProvider protocols + OpenAI/Anthropic impls
├── models/              # SQLAlchemy ORM (User, Document, Requirement, CompanyChunk, Report*, AuditLog)
├── routers/             # auth.py, uploads.py, reports.py
└── services/
    ├── parsing.py       # PDF/DOCX/TXT extraction
    ├── chunking.py      # tiktoken cl100k_base, token-aware overlap
    ├── requirements.py  # heuristic regulatory-clause splitter
    ├── retrieval.py     # pgvector cosine top-k
    ├── compliance.py    # LLM-based per-requirement evaluator
    ├── storage.py       # streaming upload to ./storage/<user>/<uuid>.<ext>
    ├── pipeline.py      # orchestrator (ingest → embed → retrieve → evaluate → persist → cleanup)
    └── audit.py         # append-only audit_logs writer

frontend/app/
├── layout.tsx
├── page.tsx             # upload + run review
├── login/page.tsx       # register / login (with data-handling acknowledgement)
└── reports/[id]/page.tsx
```

## Git workflow

- Default branch: `main` (rename `devin/initial-scaffold` if it isn't yet).
- Open PRs from `devin/<timestamp>-<topic>` style branches against `main`.
- Don't push directly to `main`.
