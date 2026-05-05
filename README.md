# Compliance Reviewer — MVP

A small full-stack web app that helps a human reviewer check a company submission against a regulatory document. The backend extracts requirements from the regulation, retrieves the most relevant passages from the submission via vector search, and asks an LLM to produce a structured per-requirement finding (compliant / partially compliant / non-compliant / not found / needs human review) with evidence quotes, an explanation, a suggested fix, and a risk level.

> **Not legal advice.** This tool assists human compliance reviewers. It is not a substitute for qualified legal counsel and must not be used to replace human judgement.

## Architecture

```
┌──────────────┐     HTTPS      ┌────────────────┐     SQL/pgvector     ┌──────────────┐
│  Next.js UI  │  ───────────►  │  FastAPI app   │  ─────────────────►  │  Postgres    │
│  (TypeScript)│                │  (Python 3.11) │                      │  + pgvector  │
└──────────────┘                └────────┬───────┘                      └──────────────┘
                                         │
                                         ▼
                              ┌────────────────────┐
                              │  LLM provider      │
                              │  (OpenAI |         │
                              │   Anthropic)       │
                              └────────────────────┘
```

```
backend/
├── app/
│   ├── main.py                  # FastAPI entrypoint, CORS, /healthz, /disclaimer
│   ├── config.py                # Settings (env vars)
│   ├── db.py                    # SQLAlchemy session + Base
│   ├── deps.py                  # JWT auth dependency
│   ├── logging_setup.py         # Filter that drops document/prompt content
│   ├── llm/                     # LLM provider abstraction
│   │   ├── base.py
│   │   ├── openai_provider.py
│   │   └── anthropic_provider.py
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic DTOs
│   ├── routers/                 # auth.py, uploads.py, reports.py
│   └── services/                # parsing, chunking, requirements,
│                                # retrieval, compliance, pipeline,
│                                # storage, audit, auth
├── alembic/                     # Migrations (incl. pgvector extension)
└── tests/                       # Unit tests for the deterministic bits

frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                 # Upload + run review
│   ├── login/page.tsx           # Register/login + acknowledgement
│   └── reports/[id]/page.tsx    # Report viewer
├── components/DisclaimerBanner.tsx
└── lib/api.ts                   # Typed fetch client
```

## Tech stack

- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind.
- **Backend**: FastAPI (Python 3.11+).
- **Database**: PostgreSQL 16 with [pgvector](https://github.com/pgvector/pgvector).
- **File parsing**: [`pypdf`](https://pypi.org/project/pypdf/), [`python-docx`](https://pypi.org/project/python-docx/), and built-in TXT decoding.
- **LLM**: provider-agnostic interface with OpenAI and Anthropic implementations selected via `LLM_PROVIDER`.
- **Embeddings**: OpenAI `text-embedding-3-small` by default.
- **Auth**: JWT bearer tokens with bcrypt-hashed passwords.

## Pipeline

1. **Upload** (auth required, server-side extension + size validation).
2. **Parse** PDF / DOCX / TXT into plain text.
3. **Extract requirements** from the regulatory document using deterministic heuristics (numbered/bulleted clauses, imperative `shall`/`must` sentences).
4. **Chunk** the company document into ~500-token windows with 50-token overlap.
5. **Embed** every requirement and chunk with the configured embedding model and store the vectors in `pgvector` columns.
6. **Retrieve** the top-k most similar company chunks for each requirement (cosine distance).
7. **Evaluate** each requirement with the LLM. The LLM is given only the retrieved excerpts and is prompted to return a strict JSON object, which the backend coerces into the `ReportFinding` schema.
8. **Persist** the structured `Report` (status, summary, findings).
9. **Privacy clean-up**: when `DELETE_SOURCE_FILES_AFTER_PROCESSING=true` (the default), the original uploaded files, requirement rows, and company chunk rows are deleted after the report is generated. Only the structured report and audit metadata remain.

### Report shape

For each requirement the report contains:

| Field              | Type                                                                           |
| ------------------ | ------------------------------------------------------------------------------ |
| `requirement_id`   | string (e.g. `R-1.2`, `R-B003`)                                                |
| `requirement_text` | string                                                                         |
| `status`           | `compliant` \| `non_compliant` \| `partially_compliant` \| `not_found` \| `needs_human_review` |
| `confidence`       | number in `[0, 1]`                                                             |
| `risk_level`       | `low` \| `medium` \| `high`                                                    |
| `explanation`      | short string                                                                   |
| `suggested_fix`    | string (may be empty if compliant)                                             |
| `evidence`         | list of `{ chunk_ordinal, quote }`                                             |

## Privacy & security

The application is designed so that as little user content as possible touches durable storage:

- **Never committed to git**: `.env`, `uploads/`, `storage/`, `tmp/`, and `*.pdf` / `*.docx` / `*.txt` files are all in `.gitignore`.
- **Secrets only in env vars**: API keys are read from `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` and are never echoed in logs or persisted.
- **No document content in logs**: `app/logging_setup.py` installs a filter that drops any log record carrying `extra={"contains_document": True}` or `contains_prompt=True`, and truncates oversized messages.
- **No prompt logging**: the compliance pipeline does not log the prompt or response bodies of LLM calls.
- **Private uploads**: files are stored under `storage/<user_id>/<document_id>.<ext>`; only the uploading user can fetch metadata or trigger a report referencing them.
- **Deletion after processing**: with `DELETE_SOURCE_FILES_AFTER_PROCESSING=true`, the pipeline:
  1. Deletes the source files from disk.
  2. Deletes the extracted requirement rows and embedded chunk rows from the database.
  3. Marks the `Document` rows as `deleted` with a `deleted_at` timestamp.
  4. Leaves only the structured `Report` (and an entry in `audit_logs`).
- **Auth required for upload**: the `POST /uploads` endpoint requires a valid JWT.
- **Acknowledgement at sign-up**: the registration UI requires the user to acknowledge that they will not upload personal or confidential data they are not authorized to share.
- **Server-side validation**: extension allow-list (`pdf,docx,txt`) and a `MAX_UPLOAD_BYTES` limit are enforced while streaming the body to disk.
- **Audit log**: `audit_logs` records who uploaded what, when, and which reports were created/completed/failed. It contains only metadata (filename, size, sha256, counts) — never document text.
- **Do not train**: do not enable any provider-side training on uploaded content. For OpenAI, API traffic is not used for training by default; for Anthropic, the same applies. Verify the setting on your account if compliance with this matters for your use case.

## Local setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for the Postgres + pgvector container)
- An OpenAI or Anthropic API key

### 1. Database

```bash
cp .env.example .env
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`. OpenAPI docs: `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
```

The UI is now at `http://localhost:3000`.

### 4. Run a review

1. Visit `http://localhost:3000`, register an account, and acknowledge the data-handling notice.
2. Upload a regulatory document (PDF/DOCX/TXT) and a company submission.
3. Click **Run review**. The pipeline runs synchronously; for very long documents this may take a minute or two.
4. The browser navigates to `/reports/<id>` with the structured findings.

## Configuration reference

All tunables live in environment variables (see [`.env.example`](./.env.example)):

| Variable                                 | Default                          | Notes                                                          |
| ---------------------------------------- | -------------------------------- | -------------------------------------------------------------- |
| `DATABASE_URL`                           | `postgresql+psycopg://…`         | SQLAlchemy URL.                                                |
| `JWT_SECRET`                             | `change-me`                      | **Always override in production.**                             |
| `JWT_EXPIRES_MINUTES`                    | `720`                            | 12 h.                                                          |
| `LLM_PROVIDER`                           | `openai`                         | `openai` or `anthropic`.                                       |
| `LLM_MODEL`                              | `gpt-4o-mini`                    | Provider-specific model id.                                    |
| `EMBEDDING_PROVIDER`                     | `openai`                         | Currently only OpenAI.                                         |
| `EMBEDDING_MODEL`                        | `text-embedding-3-small`         | Must match `EMBEDDING_DIM`.                                    |
| `EMBEDDING_DIM`                          | `1536`                           | Match the chosen embedding model's dimension.                  |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`   | _unset_                          | Set the one(s) you need.                                       |
| `DELETE_SOURCE_FILES_AFTER_PROCESSING`   | `true`                           | Privacy mode flag.                                             |
| `MAX_UPLOAD_BYTES`                       | `20971520`                       | 20 MiB.                                                        |
| `ALLOWED_UPLOAD_EXTENSIONS`              | `pdf,docx,txt`                   | Server-side allow-list.                                        |
| `STORAGE_DIR` / `TMP_DIR`                | `./storage` / `./tmp`            | Created automatically; both git-ignored.                       |
| `CHUNK_TOKEN_SIZE` / `CHUNK_TOKEN_OVERLAP` | `500` / `50`                  | Token-aware chunking (cl100k_base).                            |
| `RETRIEVAL_TOP_K`                        | `6`                              | Chunks shown to the LLM per requirement.                       |
| `CORS_ORIGINS`                           | `http://localhost:3000`          | Comma-separated.                                               |

## API reference

| Method | Path                  | Auth | Body                                                                    | Returns           |
| ------ | --------------------- | ---- | ----------------------------------------------------------------------- | ----------------- |
| POST   | `/auth/register`      | no   | `{ email, password }`                                                   | `UserOut`         |
| POST   | `/auth/login`         | no   | `{ email, password }`                                                   | `TokenResponse`   |
| POST   | `/auth/token`         | no   | OAuth2 form (`username`, `password`)                                    | `TokenResponse`   |
| GET    | `/auth/me`            | yes  | —                                                                       | `UserOut`         |
| POST   | `/uploads`            | yes  | multipart `kind=regulatory\|company`, `file=<file>`                     | `DocumentOut`     |
| GET    | `/uploads/{id}`       | yes  | —                                                                       | `DocumentOut`     |
| POST   | `/reports`            | yes  | `{ regulatory_document_id, company_document_id }`                       | `ReportOut`       |
| GET    | `/reports`            | yes  | —                                                                       | `ReportOut[]`     |
| GET    | `/reports/{id}`       | yes  | —                                                                       | `ReportOut`       |
| GET    | `/healthz`            | no   | —                                                                       | `{ status: "ok" }`|
| GET    | `/disclaimer`         | no   | —                                                                       | disclaimer text   |

## Tests

```bash
cd backend
pytest
```

Only the deterministic bits are unit-tested (requirement extraction, chunking, response coercion). The LLM and embedding calls are best exercised end-to-end with a real provider.

## License

This MVP is provided as-is, without warranty of any kind. Review carefully before using on regulated data.
