# AGENTS.md

Guidance for AI coding agents working in this repository.

## Strict privacy rules — non-negotiable

Anything that would increase the risk of leaking user document content is a **regression**. In particular:

- **Never commit user documents.** `.env`, `uploads/`, `storage/`, `tmp/`, and any `*.pdf` / `*.docx` / `*.txt` file (outside `docs/`) are git-ignored. Do not `git add -f` them.
- **Never log document contents.** Use `logger.info("…", extra={"contains_document": True})` to mark records that would carry user data; the logging filter in `app/logging_setup.py` drops them. Do not print, log, or echo prompt bodies, response bodies, requirement text, or chunk text from the pipeline.
- **Never log secrets.** API keys are loaded from environment variables and must not be embedded in error messages, log lines, or commit history.
- **Never store the full source document in the database.** The schema deliberately stores only requirement text (derived) and chunked passages (derived). After a report is generated, with `DELETE_SOURCE_FILES_AFTER_PROCESSING=true`, both rows are deleted and the file on disk is removed.
- **Never bypass the auth check on uploads.** All file ingestion routes require `get_current_user`.
- **Never call an LLM provider with a setting that opts in to training on user data.** This is enforced primarily at the provider account level; do not introduce code paths that send user content to providers without API-mode safeguards.

## Coding conventions

- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0 ORM. Use `from __future__ import annotations` at the top of every module.
- Frontend: Next.js 14 App Router, TypeScript strict mode, Tailwind. Prefer client components only where state is needed.
- Keep services pure where possible; the `routers/*` modules are the only place that should `commit()` SQLAlchemy sessions outside the pipeline.

## Tests & checks

```bash
# backend
cd backend && pytest && ruff check .

# frontend
cd frontend && npm run lint && npm run typecheck
```
