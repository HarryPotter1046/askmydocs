"""Ingest PDFs into Supabase: per-page chunk -> embed (batched) -> store.

Run:  python ingest.py              # all PDFs in docs/
      python ingest.py path/a.pdf   # specific files

Re-running is safe: existing chunks for a source are replaced, not duplicated.
"""
import os
import sys

from pypdf import PdfReader
from openai import OpenAI
from supabase import create_client

import config

config.require_env()
openai = OpenAI()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

EMBED_BATCH = 100  # inputs per embeddings request (API max is 2048)


def chunk_text(text, size=800, overlap=150):
    """Sliding-window chunker. ~800 chars with 150 overlap keeps related
    sentences together without losing context at chunk edges."""
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def embed_batch(texts):
    """Batched embeddings — one request per EMBED_BATCH chunks, not one per chunk."""
    out = []
    for i in range(0, len(texts), EMBED_BATCH):
        resp = openai.embeddings.create(model=config.EMBED_MODEL, input=texts[i:i + EMBED_BATCH])
        out.extend(d.embedding for d in resp.data)
    return out


def ingest_pdf(path):
    source = os.path.basename(path)
    reader = PdfReader(path)

    # Chunk per page so every chunk carries the page number it came from.
    page_chunks = []  # list of (page_number, chunk_text)
    for page_num, page in enumerate(reader.pages, start=1):
        for chunk in chunk_text(page.extract_text() or ""):
            page_chunks.append((page_num, chunk))

    if not page_chunks:
        print(f"Skipped {source} (no extractable text — scanned PDF?)")
        return

    embeddings = embed_batch([c for _, c in page_chunks])
    rows = [
        {"content": c, "source": source, "page": p, "chunk_index": i, "embedding": e}
        for i, ((p, c), e) in enumerate(zip(page_chunks, embeddings))
    ]
    # Idempotent: replace this source's old chunks instead of duplicating them.
    supabase.table("documents").delete().eq("source", source).execute()
    supabase.table("documents").insert(rows).execute()
    print(f"Ingested {len(rows)} chunks from {source}")


if __name__ == "__main__":
    pdfs = sys.argv[1:] or sorted(str(p) for p in config.DOCS_DIR.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"No PDFs found in {config.DOCS_DIR}. Add some, or run: python make_sample_pdfs.py")
    for pdf in pdfs:
        ingest_pdf(pdf)
