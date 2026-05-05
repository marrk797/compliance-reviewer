---
title: Compliance Reviewer Backend
emoji: 📋
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Compliance Reviewer — Backend

This is the FastAPI backend for the [Compliance Reviewer](https://github.com/marrk797/compliance-reviewer) MVP.

It assists human reviewers in checking a company submission against a regulatory document. **It does not provide legal advice.**

The frontend is deployed separately on Vercel and points to this Space's URL via `NEXT_PUBLIC_API_BASE_URL`.

## Required environment variables

Configure these in the Space's **Settings → Variables and secrets**:

- `JWT_SECRET` — long random string (required).
- `GROQ_API_KEY` — get a free key at https://console.groq.com/keys.
- `CORS_ORIGINS` — comma-separated list of frontend origins, e.g. `https://your-app.vercel.app`.

Optional:

- `LLM_MODEL` (default `llama-3.3-70b-versatile`).
- `DELETE_SOURCE_FILES_AFTER_PROCESSING` (default `true`).
- `MAX_UPLOAD_BYTES` (default 20 MiB).

## Notes

- On the free Spaces tier the filesystem is **ephemeral**: restarts will reset the SQLite database and any uploaded files. For persistence, attach the Persistent Storage addon (~$5/month) and the `/data/...` paths used by the Dockerfile will be retained.
- The first run downloads ~70 MB of embedding model weights (`BAAI/bge-small-en-v1.5`). Subsequent runs are cached.
