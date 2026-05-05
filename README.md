# Compliance Reviewer — Free MVP

A small Next.js web app that helps a human reviewer check a company submission against a regulatory document. The site extracts requirements from the regulation, retrieves the most relevant passages from the submission via local vector search, and asks the user's chosen LLM to produce a structured per-requirement finding (compliant / partially compliant / non-compliant / not found / needs human review) with evidence quotes, an explanation, a suggested fix, and a risk level.

> **Not legal advice.** This tool assists human compliance reviewers. It is not a substitute for qualified legal counsel and must not be used to replace human judgement.

## What's "free" about it

This MVP runs **entirely in the user's browser**. There is no server we run, no database we host, no API key we share. The only cost is one free Groq API key per user (no credit card).

| Layer | Choice | Why |
| --- | --- | --- |
| Hosting | **Vercel** (free tier) | Serves the Next.js static + RSC bundle. |
| LLM | **Groq** (Llama 3.3 70B by default) | Free key, no card, generous rate limit. |
| Embeddings | **Transformers.js** running `Xenova/bge-small-en-v1.5` (384 dim) | Runs in-browser via WebAssembly; ~70 MB one-time download cached in IndexedDB. |
| Vector search | **In-memory cosine** over the chunks of the document being reviewed | No DB. Fine for documents up to a few hundred pages. |
| Persistence | **`localStorage`** | Reports survive on the device that ran the review. Files are never persisted. |

### Privacy

Because everything runs in the browser:

- The original PDF/DOCX/TXT files **never leave the device**.
- Only short retrieved excerpts (top-k chunks per requirement) are sent to Groq, alongside the requirement text. The full document is not sent.
- The Groq API key is held only in the browser's `localStorage` and is sent only to `api.groq.com` directly from the user's browser.
- Generated reports are stored in the same browser's `localStorage`. There is no shared backend that could be subpoenaed or breached.

## Architecture

```
┌──────────────────────────────────────┐         ┌──────────────────────┐
│       User's browser (any tab)       │ ──────► │   api.groq.com       │
│  ┌──────────────────────────────┐    │         │   (LLM only)         │
│  │ Next.js UI on Vercel         │    │         └──────────────────────┘
│  │ ─ /settings (key entry)      │    │
│  │ ─ / (upload + run)           │
│  │ ─ /reports/[id]              │
│  └──────────────┬───────────────┘    │
│                 │                    │
│   ┌─────────────┴───────────────┐    │
│   ▼            ▼            ▼   │    │
│ pdf.js     mammoth      Transformers.js
│ (PDF)      (DOCX)       (bge-small-en-v1.5, ONNX)
│   │            │            │   │    │
│   └────────────┴────────────┘   │    │
│           in-memory cosine      │    │
│           top-k retrieval       │    │
└──────────────────────────────────────┘
```

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                  # Upload + run review (client component)
│   ├── settings/page.tsx         # Groq key entry + acknowledgement
│   └── reports/[id]/page.tsx     # Report viewer (reads localStorage)
├── components/DisclaimerBanner.tsx
├── lib/
│   ├── chunk.ts                  # Token-aware chunker
│   ├── compliance.ts             # Per-requirement LLM evaluator
│   ├── embed.ts                  # Transformers.js singleton
│   ├── groq.ts                   # Groq fetch wrapper (JSON mode)
│   ├── parse.ts                  # PDF / DOCX / TXT extraction
│   ├── pipeline.ts               # End-to-end orchestrator
│   ├── requirements.ts           # Heuristic requirement splitter
│   ├── retrieval.ts              # In-memory cosine top-k
│   ├── storage.ts                # localStorage wrappers
│   └── types.ts                  # Shared finding/report types
├── next.config.mjs               # Stubs onnxruntime-node out of webpack
├── tsconfig.json
├── package.json
└── vercel.json                   # `framework: nextjs`
```

## Pipeline

1. **Pick files** (PDF / DOCX / TXT) for the regulatory document and the company submission. They stay in the browser.
2. **Parse** both files in the browser (`pdfjs-dist`, `mammoth`, `TextDecoder`).
3. **Extract requirements** from the regulatory document with deterministic heuristics: numbered/bulleted clauses, "Article N" / "Section N" headers, and `shall` / `must` sentences. No LLM call is made for this step — it works offline.
4. **Chunk** the company document into ~500-token windows with 50-token overlap (word-count approximation, since tiktoken is not bundled in the browser).
5. **Embed** every requirement and every chunk with `Xenova/bge-small-en-v1.5` via Transformers.js. The model file is downloaded once on first use (~70 MB) and cached in IndexedDB.
6. **Retrieve** the top-k most similar company chunks for each requirement (in-memory cosine over the L2-normalised vectors).
7. **Evaluate** each requirement with Groq in JSON mode. The LLM is given only the retrieved excerpts and the requirement text; it returns a strict JSON object that we coerce into the `FindingOut` shape.
8. **Persist** the structured report to `localStorage` and route to `/reports/[id]`.

### Report shape

| Field              | Type                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------ |
| `requirement_id`   | string (e.g. `R-3.2`, `R-B007`)                                                            |
| `requirement_text` | string                                                                                     |
| `status`           | `compliant` \| `partially_compliant` \| `non_compliant` \| `not_found` \| `needs_human_review` |
| `confidence`       | float in `[0, 1]`                                                                          |
| `risk_level`       | `low` \| `medium` \| `high`                                                                |
| `explanation`      | string (1–3 sentences)                                                                     |
| `suggested_fix`    | string (empty when compliant)                                                              |
| `evidence`         | array of `{ chunk_ordinal: number \| null, quote: string }`                                 |

## Deploy to Vercel

1. **Get a free Groq key.** Visit https://console.groq.com/keys → *Create API Key*. No credit card required. Save the key somewhere safe.
2. **Import this repo into Vercel.** Visit https://vercel.com/new → *Import Git Repository* → pick `marrk797/compliance-reviewer`.
3. **Set the Root Directory.** In the import wizard (or after the project is created, in *Settings → General*), set **Root Directory = `frontend`**. Without this, Vercel won't detect Next.js because the repository root has no `package.json`.
4. **Deploy.** No environment variables are required at build time. The Groq key is entered by each user at runtime on `/settings`.
5. After the first deploy, open the site → it will redirect you to `/settings`. Paste your Groq key, accept the disclaimer, and click *Save and continue*. The key is verified against `api.groq.com` and stored in your browser's `localStorage` only.

## Local development

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

Required: Node 18+. No other tooling, no databases, no Docker.

The first review you run in any browser will block on a one-time ~70 MB download of the embedding model into IndexedDB; subsequent reviews use the cache.

## Configuration

There are **no build-time environment variables**. All configuration is per-user, runtime, and stored in the browser:

| `localStorage` key                       | What it stores                          | Set on        |
| ---------------------------------------- | --------------------------------------- | ------------- |
| `compliance_reviewer:groq_api_key`       | The user's Groq key                     | `/settings`   |
| `compliance_reviewer:groq_model`         | Override Groq model (default `llama-3.3-70b-versatile`) | `/settings` |
| `compliance_reviewer:acknowledged`       | "I won't upload confidential data" flag | `/settings`   |
| `compliance_reviewer:reports`            | The structured reports (no source docs) | After each run |

Clearing the site's localStorage in DevTools (or clicking *Clear local settings* in `/settings`) wipes everything.

## Tech notes

- The `next.config.mjs` aliases `onnxruntime-node$` and `sharp$` to `false` so webpack does not try to bundle Transformers.js' Node-only fallback (which contains `.node` native binaries that webpack cannot parse). This is the configuration recommended by the [Transformers.js Next.js tutorial](https://huggingface.co/docs/transformers.js/tutorials/next).
- We use `@xenova/transformers@2` rather than `@huggingface/transformers@3` (the rename) because the v3 prebuilt webpack bundle does not currently re-bundle cleanly inside Next.js 14.
- We use `groq-sdk` with `dangerouslyAllowBrowser: true`. This is acceptable here because each user provides their own key in the UI; there is no shared key embedded in the bundle.
- PDF.js loads its worker from a CDN URL (`cdn.jsdelivr.net/npm/pdfjs-dist@4.7.76/build/pdf.worker.min.mjs`) so we don't have to wire the worker into Next.js' static asset pipeline.

## Scripts

```bash
cd frontend
npm run lint        # ESLint
npm run typecheck   # tsc --noEmit
npm run build       # Production build
npm run dev         # Local dev server on :3000
```

## License

MIT.
