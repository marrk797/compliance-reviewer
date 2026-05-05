# Compliance Reviewer — Backend

FastAPI service that powers the compliance review pipeline. See the [project README](../README.md) for the full architecture and setup instructions.

Quick start:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env   # then edit values
alembic upgrade head
uvicorn app.main:app --reload
```
