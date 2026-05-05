# Compliance Reviewer — Backend

FastAPI service that powers the compliance review pipeline. See the [project README](../README.md) for the full architecture and free-deploy instructions (Vercel + Hugging Face Spaces).

Quick start:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env   # then edit values (at minimum: GROQ_API_KEY)
uvicorn app.main:app --reload
```

The first call that needs an embedding will download ~70 MB of model weights into a local cache.

The schema (regular tables + the `company_chunks_vec` virtual table) is created automatically on startup by `init_db()`.
