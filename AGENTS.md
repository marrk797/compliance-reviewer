# AGENTS.md

Guidance for AI coding agents working in this repository.

## Architecture

This is a **browser-only** Next.js application deployed on Vercel. There is no backend service:

- Document parsing (PDF/DOCX/TXT), embedding (Transformers.js / `Xenova/bge-small-en-v1.5`), retrieval, and Groq LLM calls all run in the user's browser.
- The user pastes their own free Groq API key on the `/settings` page; the key is held only in `localStorage` and is sent only to `api.groq.com`.
- Generated reports are persisted to `localStorage` so they survive page reloads on the same device.

## Strict privacy rules — non-negotiable

Anything that would increase the risk of leaking user document content is a **regression**. In particular:

- **Never upload user documents to a server.** This app's whole privacy story is "files never leave the browser." Do not introduce server-side upload endpoints, telemetry that includes file contents, or analytics that captures uploaded text.
- **Never log document contents to a server.** It's fine to use `console.log` for local debugging during development, but never wire those logs to a remote sink.
- **Never embed a shared API key.** Each user pastes their own Groq key. Do not introduce a shared key, a proxy that injects a key, or any mechanism that lets one user's traffic flow through another's account.
- **Never commit user documents.** `.env`, `uploads/`, `storage/`, `tmp/`, and any `*.pdf` / `*.docx` / `*.txt` (outside `docs/`) are git-ignored.
- **Never call an LLM provider with a setting that opts in to training on user data.** Groq does not train on API traffic by default; do not change defaults.

## Coding conventions

- Frontend: Next.js 14 App Router, TypeScript strict mode, Tailwind. Browser-only modules in `frontend/lib/` are pure and side-effect-free at import time; the embedding singleton is gated on `typeof window`.
- Use `"use client"` for any component that needs `localStorage`, `File`, or the embedding/Groq pipeline.
- Keep `frontend/lib/` provider-agnostic where possible: `groq.ts` is the only module that knows about Groq specifically.

## Tests & checks

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```
