"""AskMyDocs RAG endpoint: embed question -> retrieve grounded chunks -> Claude.

Run:  uvicorn app:app --reload
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from anthropic import Anthropic
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
openai = OpenAI()
claude = Anthropic()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tune against your demo data — see "Threshold tuning" in the plan/README.
MATCH_THRESHOLD = 0.3
NOT_FOUND = "I couldn't find that in the provided documents."


class Query(BaseModel):
    question: str


def embed(text):
    return openai.embeddings.create(
        model="text-embedding-3-small", input=text
    ).data[0].embedding


@app.post("/ask")
def ask(q: Query):
    q_vec = embed(q.question)
    res = supabase.rpc("match_documents", {
        "query_embedding": q_vec,
        "match_count": 4,
        "match_threshold": MATCH_THRESHOLD,
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
        model="claude-sonnet-4-6",        # swap to "claude-opus-4-8" for max quality
        max_tokens=500,
        system=system,
        messages=[{
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {q.question}",
        }],
    )
    answer = "".join(b.text for b in msg.content if b.type == "text")

    citations = [
        {"source": c["source"], "page": c["page"], "similarity": round(c["similarity"], 3)}
        for c in chunks
    ]
    return {"answer": answer, "citations": citations}
