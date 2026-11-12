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

```bash
pip install -r requirements.txt
cp .env.example .env          # then fill in your keys
```

1. **Database** — run [`schema.sql`](schema.sql) in the Supabase SQL editor
   (creates the `documents` table + `match_documents` function).
2. **Demo data** — `pip install reportlab && python make_sample_pdfs.py`
   (writes refund / shipping / warranty PDFs into `docs/`), or drop your own PDFs in `docs/`.
3. **Ingest** — `python ingest.py`
4. **Serve** — `uvicorn app:app --reload`
5. **Chat** — open `index.html` in a browser.

## Demo script (the 90-second Loom)

1. Show the `docs/` folder of sample PDFs.
2. Run `python ingest.py` → chunks get embedded and stored.
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

`MATCH_THRESHOLD` in [`app.py`](app.py) defaults to `0.3` — a starting point, not a
magic number. After ingesting your docs, read the `similarity` values the `/ask`
endpoint returns for real vs. out-of-scope questions, and set the threshold just below
your worst legitimate match and above the best junk match.

## Project layout

```
schema.sql          # Supabase table + match_documents()
ingest.py           # PDFs -> per-page chunks -> embeddings -> Supabase
app.py              # FastAPI /ask endpoint (retrieve + generate)
index.html          # minimal chat UI
make_sample_pdfs.py # optional: generate demo PDFs into docs/
docs/               # your source PDFs
```
