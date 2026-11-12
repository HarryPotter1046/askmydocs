"""AskMyDocs RAG endpoint: embed question -> retrieve grounded chunks -> Claude.

Run:  uvicorn app:app --reload   then open http://localhost:8000
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from anthropic import Anthropic
from supabase import create_client

import config

config.require_env()
openai = OpenAI()
claude = Anthropic()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

app = FastAPI(title="AskMyDocs")
# Only needed if index.html is opened from file:// or another origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

NOT_FOUND = "I couldn't find that in the provided documents."


class Query(BaseModel):
    question: str


def embed(text):
    return openai.embeddings.create(model=config.EMBED_MODEL, input=text).data[0].embedding


@app.get("/")
def index():
    return FileResponse(config.ROOT / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "model": config.CLAUDE_MODEL, "threshold": config.MATCH_THRESHOLD}


@app.post("/ask")
def ask(q: Query):
    question = q.question.strip()
    if not question:
        raise HTTPException(400, "question must not be empty")

    q_vec = embed(question)
    res = supabase.rpc("match_documents", {
        "query_embedding": q_vec,
        "match_count": config.MATCH_COUNT,
        "match_threshold": config.MATCH_THRESHOLD,
    }).execute()
    chunks = res.data or []

    # Robust "I don't know": nothing cleared the bar -> don't even call Claude.
    if not chunks:
        return {"answer": NOT_FOUND, "citations": []}

    context = "\n\n".join(
        f"[{i + 1}] (source: {c['source']}, page {c['page']})\n{c['content']}"
        for i, c in enumerate(chunks)
    )
    system = (
        "You are a support agent. Answer the question using ONLY the context provided. "
        f"If the answer is not in the context, reply exactly: '{NOT_FOUND}' "
        "Do NOT mention or list sources in your answer — the UI displays them separately."
    )
    msg = claude.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=config.MAX_TOKENS,
        system=system,
        messages=[{
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        }],
    )
    answer = "".join(b.text for b in msg.content if b.type == "text")

    citations = [
        {"source": c["source"], "page": c["page"], "similarity": round(c["similarity"], 3)}
        for c in chunks
    ]
    return {"answer": answer, "citations": citations}
