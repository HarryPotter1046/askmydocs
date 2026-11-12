"""Ingest PDFs into Supabase: per-page chunk -> embed (batched) -> store.

Run once per document set:  python ingest.py
Drop your PDFs in docs/ first (or run make_sample_pdfs.py to generate demo data).
"""
import os
import glob

from pypdf import PdfReader
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
openai = OpenAI()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def chunk_text(text, size=800, overlap=150):
    """Sliding-window chunker. ~800 chars with 150 overlap keeps related
    sentences together without losing context at chunk edges."""
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def embed_batch(texts):
    """One embeddings call for the whole document, not one per chunk."""
    resp = openai.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]


def ingest_pdf(path):
    source = os.path.basename(path)
    reader = PdfReader(path)

    # Chunk per page so every chunk carries the page number it came from.
    page_chunks = []  # list of (page_number, chunk_text)
    for page_num, page in enumerate(reader.pages, start=1):
        for chunk in chunk_text(page.extract_text() or ""):
            page_chunks.append((page_num, chunk))

    if not page_chunks:
        print(f"Skipped {source} (no extractable text)")
        return

    embeddings = embed_batch([c for _, c in page_chunks])
    rows = [
        {"content": c, "source": source, "page": p, "chunk_index": i, "embedding": e}
        for i, ((p, c), e) in enumerate(zip(page_chunks, embeddings))
    ]
    supabase.table("documents").insert(rows).execute()
    print(f"Ingested {len(rows)} chunks from {source}")


if __name__ == "__main__":
    pdfs = glob.glob("docs/*.pdf")
    if not pdfs:
        print("No PDFs found in docs/. Add some, or run: python make_sample_pdfs.py")
    for pdf in pdfs:
        ingest_pdf(pdf)
