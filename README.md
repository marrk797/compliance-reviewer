# Compliance Reviewer — Free MVP

A small full-stack web app that helps a human reviewer check a company submission against a regulatory document. The backend extracts requirements from the regulation, retrieves the most relevant passages from the submission via vector search, and asks an LLM to produce a structured per-requirement finding (compliant / partially compliant / non-compliant / not found / needs human review) with evidence quotes, an explanation, a suggested fix, and a risk level.

> **Not legal advice.** This tool assists human compliance reviewers. It is not a substitute for qualified legal counsel and must not be used to replace human judgement.

This MVP is intentionally optimised for a **fully free, no-credit-card** deployment:

| Layer | Choice | Why |
| --- | --- | --- |
| LLM | **Groq** (Llama 3.3 70B) | Free tier, no card. One key. |
| Embeddings | **fastembed** (`BAAI/bge-small-en-v1.5`, 384 dim) | ONNX, runs in-process, no key, no rate limits. |
| Database + vectors | **SQLite + sqlite-vec** | Zero signup, single file, vec0 virtual table for top-k. |
| Frontend host | **Vercel** | Free, GitHub-connected, auto deploys on push. |
| Backend host | **Hugging Face Spaces** (Docker SDK) | Free, runs the included `Dockerfile`. |

## Architecture

```
┌──────────────────────┐     HTTPS      ┌────────────────────────┐
│  Next.js UI (Vercel) │ ─────────────► │  FastAPI on HF Spaces  │
└──────────────────────┘                └──────────┬─────────────┘
                                                   │
                                ┌──────────────────┼─────────────────┐
                                ▼                  ▼                 ▼
                       ┌──────────────┐  ┌──────────────────┐  ┌──────────┐
                       │ Groq LLM API │  │ SQLite +sqlite-vec│  │ fastembed │
                       │ (Llama 3.3)  │  │ (single file DB) │  │ (in-proc) │
                       └──────────────┘  └──────────────────┘  └──────────┘
```

```
backend/
├── app/
│   ├── main.py                  # FastAPI entrypoint, CORS, /healthz, /disclaimer, init_db()
│   ├── config.py                # Settings (env vars)
│   ├── db.py                    # SQLAlchemy engine + sqlite-vec extension loader
│   ├── deps.py                  # JWT auth dependency
│   ├── logging_setup.py         # Filter that drops document/prompt content
│   ├── llm/                     # LLM provider abstraction
│   │   ├── base.py
│   │   ├── groq_provider.py     # default
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── fastembed_provider.py
│   ├── models/                  # SQLAlchemy ORM models (UUIDs, JSON, Enum)
│   ├── schemas/                 # Pydantic DTOs
│   ├── routers/                 # auth.py, uploads.py, reports.py
│   └── services/                # parsing, chunking, requirements,
│                                # retrieval (sqlite-vec), compliance,
│                                # pipeline, storage, audit, auth
└── tests/                       # Unit tests for the deterministic bits

frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                 # Upload + run review
│   ├── login/page.tsx           # Register/login + acknowledgement
│   └── reports/[id]/page.tsx    # Report viewer
├── components/DisclaimerBanner.tsx
└── lib/api.ts                   # Typed fetch client

Dockerfile                        # Backend container for HF Spaces
HUGGINGFACE_SPACE_README.md       # Frontmatter you copy into the Space's README
```

## Pipeline

1. **Upload** (auth required, server-side extension + size validation).
2. **Parse** PDF / DOCX / TXT into plain text.
3. **Extract requirements** from the regulatory document using deterministic heuristics (numbered/bulleted clauses, imperative `shall`/`must` sentences).
4. **Chunk** the company document into ~500-token windows with 50-token overlap.
5. **Embed** every requirement and chunk locally with fastembed; chunk vectors are stored in the `company_chunks_vec` virtual table.
6. **Retrieve** the top-k most similar company chunks for each requirement (cosine distance via sqlite-vec).
7. **Evaluate** each requirement with Groq. The LLM is given only the retrieved excerpts and is prompted to return a strict JSON object, which the backend coerces into the `ReportFinding` schema.
8. **Persist** the structured `Report` (status, summary, findings).
9. **Privacy clean-up**: when `DELETE_SOURCE_FILES_AFTER_PROCESSING=true` (the default), the original uploaded files, requirement rows, chunk rows, *and* their vec0 embeddings are deleted after the report is generated. Only the structured report and audit metadata remain.

### Report shape

| Field              | Type                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------ |
| `requirement_id`   | string (e.g. `R-1.2`, `R-B003`)                                                            |
| `requirement_text` | string                                                                                     |
| `status`           | `compliant` \| `non_compliant` \| `partially_compliant` \| `not_found` \| `needs_human_review` |
| `confidence`       | number in `[0, 1]`                                                                         |
| `risk_level`       | `low` \| `medium` \| `high`                                                                |
| `explanation`      | short string                                                                               |
| `suggested_fix`    | string                                                                                     |
| `evidence`         | list of `{ chunk_ordinal, quote }`                                                         |

## Privacy & security

- **Never committed to git**: `.env`, `uploads/`, `storage/`, `tmp/`, `data/`, SQLite files, and `*.pdf` / `*.docx` / `*.txt` are all in `.gitignore`.
- **Secrets only in env vars**: API keys are read from `GROQ_API_KEY` (or `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`) and are never echoed in logs or persisted.
- **No document content in logs**: `app/logging_setup.py` installs a filter that drops any log record carrying `extra={"contains_document": True}` or `contains_prompt=True`, and truncates oversized messages.
- **No prompt logging**: the compliance pipeline does not log the prompt or response bodies of LLM calls.
- **Private uploads**: files are stored under `storage/<user_id>/<document_id>.<ext>`; only the uploading user can fetch metadata or trigger a report referencing them.
- **Deletion after processing** with `DELETE_SOURCE_FILES_AFTER_PROCESSING=true` (default) deletes the file, the requirement rows, the chunk rows, and the vec0 embeddings, then marks the document `deleted`.
- **Auth required for upload**: `POST /uploads` depends on `get_current_user`.
- **Acknowledgement at sign-up**: the registration UI requires the user to acknowledge that they will not upload personal or confidential data they are not authorized to share.
- **Server-side validation**: extension allow-list (`pdf,docx,txt`) and a `MAX_UPLOAD_BYTES` limit, enforced while streaming the body to disk.
- **Audit log** records who uploaded what, when, and which reports were created/completed/failed (metadata only, no document text).
- **Do not train**: don't enable any provider-side training on uploaded content. Groq, OpenAI, and Anthropic do not train on API traffic by default; verify on your account.

## Deploy for free

### 1. Backend on Hugging Face Spaces

1. Get a free Groq key (no card): https://console.groq.com/keys
2. Sign up at https://huggingface.co/join and create a new Space:
   https://huggingface.co/new-space
   - **Owner**: your username
   - **Space name**: `compliance-reviewer-api` (or anything)
   - **License**: MIT
   - **Space SDK**: **Docker** → **Blank**
   - Visibility: Public or Private
3. Click **Create Space**.
4. On the Space page, go to **Settings → Variables and secrets** and add:
   - `JWT_SECRET` = (a long random string — `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
   - `GROQ_API_KEY` = your Groq key
   - `CORS_ORIGINS` = (leave blank for now — you'll fill it in after Vercel deploys)
5. Push this repo's contents into the Space's git remote:
   ```bash
   # In a fresh checkout of this repo:
   git remote add space https://huggingface.co/spaces/<your-hf-user>/compliance-reviewer-api
   # The Space's README controls the Space metadata (sdk, port, etc.).
   # Use the curated frontmatter included in this repo:
   cp HUGGINGFACE_SPACE_README.md README.md
   git add README.md && git commit -m "HF Space frontmatter"
   git push space HEAD:main
   ```
   Or, simpler: in the Space's "Files" tab on the website, drag-and-drop the contents of this repo (or just `Dockerfile` + `backend/` + `HUGGINGFACE_SPACE_README.md` renamed to `README.md`).
6. The Space will build the Docker image (~3-5 min the first time). Once it's "Running", the public URL looks like:
   `https://<your-hf-user>-compliance-reviewer-api.hf.space`
   Test it: `curl https://<your-hf-user>-compliance-reviewer-api.hf.space/healthz` → `{"status":"ok"}`

### 2. Frontend on Vercel

1. Sign in at https://vercel.com (free, GitHub auth).
2. **New Project** → **Import** the GitHub repo `marrk797/compliance-reviewer`.
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework**: Next.js (auto-detected)
   - **Environment Variables**:
     - `NEXT_PUBLIC_API_BASE_URL` = the HF Space URL from step 1 (e.g. `https://<user>-compliance-reviewer-api.hf.space`)
4. Click **Deploy**. Build takes ~1-2 min.
5. You'll get a URL like `https://compliance-reviewer.vercel.app`.

### 3. Wire CORS

1. Back in the HF Space's **Settings → Variables and secrets**, set `CORS_ORIGINS` to your Vercel URL (e.g. `https://compliance-reviewer.vercel.app,https://compliance-reviewer-<hash>.vercel.app`).
2. Restart the Space (Settings → Factory rebuild).

You're done. Visit your Vercel URL, register an account, upload a regulatory PDF + a company submission, and run a review.

## Run locally (no deploy)

```bash
cp .env.example .env
# put GROQ_API_KEY=... in .env

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload   # http://localhost:8000

cd ../frontend
npm install
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev                     # http://localhost:3000
```

The first request that needs an embedding will download ~70 MB of model weights into the local fastembed cache; subsequent runs are instant.

## Configuration reference

All tunables live in environment variables (see [`.env.example`](./.env.example)):

| Variable                                 | Default                          | Notes                                                          |
| ---------------------------------------- | -------------------------------- | -------------------------------------------------------------- |
| `DATABASE_PATH`                          | `./data/data.sqlite`             | On HF Spaces, set to `/data/data.sqlite` (or `/tmp/data.sqlite` on free tier). |
| `JWT_SECRET`                             | `change-me`                      | **Always override in production.**                             |
| `JWT_EXPIRES_MINUTES`                    | `720`                            | 12 h.                                                          |
| `LLM_PROVIDER`                           | `groq`                           | `groq`, `openai`, or `anthropic`.                              |
| `LLM_MODEL`                              | `llama-3.3-70b-versatile`        | Provider-specific model id.                                    |
| `GROQ_API_KEY`                           | _unset_                          | Free at https://console.groq.com/keys                          |
| `EMBEDDING_PROVIDER`                     | `fastembed`                      | `fastembed` (local) or `openai`.                               |
| `EMBEDDING_MODEL`                        | `BAAI/bge-small-en-v1.5`         | Must match `EMBEDDING_DIM`.                                    |
| `EMBEDDING_DIM`                          | `384`                            | Match the chosen embedding model.                              |
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

## License

MIT. Provided as-is, without warranty. Review carefully before using on regulated data.
