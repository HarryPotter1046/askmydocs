"""Shared configuration for ingest.py and app.py.

Loads .env, validates required secrets up front (clear error instead of a bare
KeyError), and centralises tunables so they can be overridden via env vars.
"""
import os
import sys
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"

load_dotenv(ROOT / ".env")

REQUIRED = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]


def require_env():
    """Exit with a clear message if a secret is unset or still the .env.example value."""
    placeholders = dotenv_values(ROOT / ".env.example")
    missing = [k for k in REQUIRED if not os.getenv(k) or os.getenv(k) == placeholders.get(k)]
    if missing:
        sys.exit(
            f"Missing/placeholder env vars: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill them in ({ROOT / '.env'})."
        )


# Embeddings — must match the vector(N) dimension in schema.sql.
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# Generation
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))

# Retrieval — tune MATCH_THRESHOLD against your data (see README).
MATCH_COUNT = int(os.getenv("MATCH_COUNT", "4"))
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.3"))
