-- AskMyDocs — Supabase schema. Run in the Supabase SQL editor (safe to re-run).

-- pgvector for similarity search
create extension if not exists vector;

-- Document chunks + their embeddings
create table if not exists documents (
  id bigserial primary key,
  content text,                 -- the chunk text
  source text,                  -- e.g. "refund_policy.pdf"
  page int,                     -- page number, for citation
  chunk_index int,              -- position within the source doc
  embedding vector(1536)        -- 1536 dims = text-embedding-3-small
);

-- Lets ingest.py replace a document's chunks quickly on re-ingest.
create index if not exists documents_source_idx on documents (source);

-- Cosine-similarity search with a relevance floor.
-- `<=>` is pgvector's cosine-distance operator; `1 - distance` is a 0–1 similarity.
-- Chunks below `match_threshold` are dropped, so an out-of-scope question can return
-- zero rows and the API answers "I couldn't find that" without guessing.
create or replace function match_documents (
  query_embedding vector(1536),
  match_count int default 4,
  match_threshold float default 0.3
)
returns table (id bigint, content text, source text, page int, similarity float)
language sql stable
as $$
  select documents.id, documents.content, documents.source, documents.page,
         1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;

-- Not needed at demo scale (a few hundred chunks = instant exact scan).
-- For production, uncomment:
-- create index if not exists documents_embedding_idx on documents using hnsw (embedding vector_cosine_ops);
