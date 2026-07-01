"""
Centralized application settings loaded from environment variables.

All configuration values are read from the .env file (via python-dotenv)
with sensible defaults so the app works out of the box for local development.
"""

from dotenv import load_dotenv
import os

# Load .env file from the project root
load_dotenv()

# ─── Groq LLM ───────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ─── Embeddings (BGE) ───────────────────────────────────
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")  # "cuda" if GPU available

# ─── Chunking ───────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

# ─── Retrieval ──────────────────────────────────────────
TOP_K: int = int(os.getenv("TOP_K", "5"))

# ─── LLM Generation ────────────────────────────────────
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "800"))

# ─── Vector Store ───────────────────────────────────────
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "hdfc_funds")

# ─── Scraper ────────────────────────────────────────────
SCRAPER_WAIT_TIME: int = int(os.getenv("SCRAPER_WAIT_TIME", "5"))  # seconds to wait for JS render
SCRAPER_RATE_LIMIT: int = int(os.getenv("SCRAPER_RATE_LIMIT", "2"))  # seconds between requests
