# AskMyDocs — RAG Support Agent

An AI support agent that answers customer questions using **only** your company's
documents — and cites the exact source (file + page) for every answer, so it never
makes things up. Ask something the docs don't cover and it says so, instead of
hallucinating.

## Architecture

```
INGESTION   PDFs ─► per-page chunk ─► embed (OpenAI, batched) ─► store in Supabase (pgvector)
QUERY       question ─► embed ─► vector search (top-k above threshold) ─► Claude ─► grounded answer + page citation
```

Five moving parts: **chunk → embed → store → retrieve → generate.**

| Layer | Tool |
|---|---|
| Vector store | Supabase + pgvector |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
| Generation | Claude `claude-sonnet-4-6` (swap to `claude-opus-4-8` for max quality) |
| Backend | Python + FastAPI |
| Frontend | Single static `index.html` |

## Setup

Requires **Python 3.10+**, a [Supabase](https://supabase.com) project, and OpenAI + Anthropic API keys.

```bash
make setup        # creates .venv, installs pinned deps, copies .env.example -> .env
```

<details><summary>Without make</summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Then use `python make_sample_pdfs.py`, `python ingest.py`, `uvicorn app:app --reload`.
</details>

1. **Keys** — fill in `.env`. `SUPABASE_KEY` is the *service-role* key
   (Project Settings → API). The scripts refuse to start while any value is
   still the `.env.example` placeholder.
2. **Database** — paste [`schema.sql`](schema.sql) into the Supabase SQL editor and run it
   (creates the `documents` table + `match_documents` function; safe to re-run).
3. **Demo data** — `make sample` writes refund / shipping / warranty PDFs into `docs/`,
   or drop your own PDFs there.
4. **Ingest** — `make ingest`. Safe to re-run: a re-ingested file's old chunks are
   replaced, not duplicated. Ingest specific files with `python ingest.py path/to/file.pdf`.
5. **Serve + chat** — `make serve`, then open **http://localhost:8000**
   (the API serves the UI; `GET /health` shows the active model and threshold).

### Configuration

Optional overrides in `.env` (defaults in [`config.py`](config.py)):

| Var | Default | Notes |
|---|---|---|
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | e.g. `claude-sonnet-5-5`, or `claude-opus-5-5` for max quality |
| `MAX_TOKENS` | `1024` | answer length cap |
| `MATCH_COUNT` | `4` | chunks retrieved per question |
| `MATCH_THRESHOLD` | `0.3` | similarity floor — see tuning below |
| `EMBED_MODEL` | `text-embedding-3-small` | must match `vector(1536)` in `schema.sql`; re-ingest if changed |
| `CORS_ORIGINS` | `*` | comma-separated; only matters if the UI is hosted elsewhere |

### Troubleshooting

- **`Missing/placeholder env vars`** — `.env` still has template values.
- **`Could not find the function match_documents`** / `relation "documents" does not exist` — run `schema.sql`.
- **Every question returns "I couldn't find that"** — nothing ingested yet, or `MATCH_THRESHOLD` too high.
- **`Skipped X (no extractable text)`** — scanned/image PDF; OCR it first.

## Demo script (the 90-second Loom)

1. Show the `docs/` folder of sample PDFs.
2. Run `make ingest` → chunks get embedded and stored.
3. Ask: *"What's your refund policy for orders over 30 days?"*
   → grounded answer **+ "Sources: refund_policy.pdf (p.1)"**.
4. Ask something not in the docs: *"Do you ship to Antarctica?"*
   → *"I couldn't find that in the provided documents."* — no hallucination.

The "I don't know" moment is what makes a client trust it. Don't skip it.

## How the no-hallucination behavior works

- **Retrieval floor** — `match_documents` drops chunks below a cosine-similarity
  `match_threshold`. An out-of-scope question returns zero rows, so the API replies
  "I couldn't find that" *without even calling the model*.
- **Grounded prompt** — Claude is instructed to answer ONLY from the retrieved context
  and to use the exact refusal string otherwise.
- **Structured citations** — the API returns `citations[]` (source, page, similarity);
  the UI renders them, so the citation can't drift from what was actually retrieved.

### Threshold tuning (once, before recording)

`MATCH_THRESHOLD` (env var, see [`config.py`](config.py)) defaults to `0.3` — a starting point, not a
magic number. After ingesting your docs, read the `similarity` values the `/ask`
endpoint returns for real vs. out-of-scope questions, and set the threshold just below
your worst legitimate match and above the best junk match, then restart the server.

## Project layout

```
schema.sql          # Supabase table + match_documents()
config.py           # env loading/validation + tunables shared by both scripts
Makefile            # setup / sample / ingest / serve shortcuts
ingest.py           # PDFs -> per-page chunks -> embeddings -> Supabase
app.py              # FastAPI: / (UI), /health, /ask (retrieve + generate)
index.html          # minimal chat UI
make_sample_pdfs.py # optional: generate demo PDFs into docs/
docs/               # your source PDFs
```
