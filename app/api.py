"""
FastAPI Backend for the HDFC Mutual Fund RAG Chatbot.

Exposes the QueryPipeline as a production-grade REST API:
  GET  /api/health              — liveness check
  GET  /api/funds               — list all 5 covered funds
  POST /api/chat                — main chat endpoint
  GET  /api/chat/history/{id}   — session conversation history
  DELETE /api/chat/history/{id} — clear a session

Swagger UI: http://localhost:8000/docs
ReDoc:      http://localhost:8000/redoc

Run:
    uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ── Add project root to path ──────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from pipeline.query import QueryPipeline
from vectorstore.store import VectorStore
from config.settings import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("api")

# ── Fund catalogue (single source of truth) ───────────────────────────────────
FUND_CATALOGUE = [
    {
        "name":         "HDFC Mid Cap Fund Direct Growth",
        "slug":         "hdfc-mid-cap-fund-direct-growth",
        "category":     "Equity",
        "sub_category": "Mid Cap",
        "url":          "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "risk":         "Very High",
        "color":        "#6C63FF",   # indigo — used by frontend
    },
    {
        "name":         "HDFC Large Cap Fund Direct Growth",
        "slug":         "hdfc-large-cap-fund-direct-growth",
        "category":     "Equity",
        "sub_category": "Large Cap",
        "url":          "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "risk":         "Very High",
        "color":        "#10B981",   # emerald
    },
    {
        "name":         "HDFC Small Cap Fund Direct Growth",
        "slug":         "hdfc-small-cap-fund-direct-growth",
        "category":     "Equity",
        "sub_category": "Small Cap",
        "url":          "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        "risk":         "Very High",
        "color":        "#F59E0B",   # amber
    },
    {
        "name":         "HDFC Gold ETF Fund of Fund Direct Plan Growth",
        "slug":         "hdfc-gold-etf-fund-of-fund-direct-plan-growth",
        "category":     "Commodity",
        "sub_category": "Gold",
        "url":          "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
        "risk":         "High",
        "color":        "#EF4444",   # rose
    },
    {
        "name":         "HDFC Silver ETF FoF Direct Growth",
        "slug":         "hdfc-silver-etf-fof-direct-growth",
        "category":     "Commodity",
        "sub_category": "Silver",
        "url":          "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
        "risk":         "High",
        "color":        "#8B5CF6",   # violet
    },
]

# ── Suggested quick questions ─────────────────────────────────────────────────
SUGGESTED_QUESTIONS = [
    "What is the NAV of HDFC Mid Cap Fund?",
    "Compare the 5Y returns of all HDFC funds",
    "What is the expense ratio of HDFC Gold ETF FoF?",
    "Who manages HDFC Small Cap Fund?",
    "What is the exit load for HDFC Large Cap Fund?",
    "What are the top holdings of HDFC Mid Cap Fund?",
    "What is the Sharpe ratio of HDFC Small Cap Fund?",
    "What is the minimum SIP for HDFC Silver ETF FoF?",
]

# ── Singleton state ───────────────────────────────────────────────────────────
_pipeline: Optional[QueryPipeline] = None
_sessions: dict[str, list[dict]]   = {}  # session_id → message history


# ── Lifespan (replaces on_event in modern FastAPI) ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the RAG pipeline once at startup, release at shutdown."""
    global _pipeline
    log.info("Loading RAG pipeline (BGE model + ChromaDB)...")
    _pipeline = QueryPipeline()
    log.info("RAG pipeline ready.")
    yield
    log.info("Shutting down.")
    _pipeline = None


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="HDFC Mutual Fund RAG API",
    description=(
        "RAG-powered chatbot API for 5 HDFC Mutual Fund schemes.\n\n"
        "Data sourced from Groww.in via Selenium scraping + `__NEXT_DATA__` extraction.\n"
        "Embeddings: BAAI/bge-small-en-v1.5 · Vector DB: ChromaDB · LLM: Groq llama-3.1-8b-instant"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS middleware — configurable origins for deployment ─────────────────────
# Set ALLOWED_ORIGINS env var (comma-separated) to add your Vercel frontend URL
# e.g. ALLOWED_ORIGINS=https://your-app.vercel.app,https://custom-domain.com
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
]
_extra_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    elapsed = int((time.time() - t0) * 1000)
    log.info(f"{request.method} {request.url.path} → {response.status_code}  ({elapsed}ms)")
    return response


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query:      str = Field(..., min_length=3, max_length=500, description="User's question")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Session ID for conversation history. Auto-generated if not provided.",
    )
    debug: bool = Field(False, description="Include retrieved chunks and intent in response")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query":      "What is the NAV of HDFC Mid Cap Fund?",
                    "session_id": "user-abc123",
                    "debug":      False,
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    answer:           str
    query:            str
    session_id:       str
    source_funds:     list[str]
    source_sections:  list[str]
    source_urls:      list[str]
    num_chunks:       int
    context_summary:  str
    model:            str
    input_tokens:     int
    output_tokens:    int
    response_time_ms: int
    # Only present when debug=True
    retrieved_chunks: Optional[list[dict]] = None
    intent:           Optional[dict]       = None


class FundInfo(BaseModel):
    name:         str
    slug:         str
    category:     str
    sub_category: str
    url:          str
    risk:         str
    color:        str


class FundsResponse(BaseModel):
    funds: list[FundInfo]
    total: int
    suggested_questions: list[str]


class HistoryResponse(BaseModel):
    session_id: str
    messages:   list[dict]
    count:      int


class HealthResponse(BaseModel):
    status:          str
    pipeline_loaded: bool
    chunks_in_db:    int
    collection:      str
    version:         str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health():
    """Liveness check — returns API status and vector store chunk count."""
    store = VectorStore(
        collection_name=CHROMA_COLLECTION_NAME,
        persist_dir=CHROMA_PERSIST_DIR,
    )
    return HealthResponse(
        status          = "ok",
        pipeline_loaded = _pipeline is not None,
        chunks_in_db    = store.count(),
        collection      = CHROMA_COLLECTION_NAME,
        version         = "1.0.0",
    )


@app.get(
    "/api/funds",
    response_model=FundsResponse,
    summary="List all covered funds",
    tags=["Funds"],
)
async def get_funds():
    """Returns metadata for all 5 HDFC funds including colour codes for the frontend."""
    return FundsResponse(
        funds               = [FundInfo(**f) for f in FUND_CATALOGUE],
        total               = len(FUND_CATALOGUE),
        suggested_questions = SUGGESTED_QUESTIONS,
    )


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Send a chat message",
    tags=["Chat"],
)
async def chat(req: ChatRequest):
    """
    Main chat endpoint. Runs the full RAG pipeline:
    1. Intent detection (fund + section keywords)
    2. Filtered vector search (ChromaDB)
    3. Prompt construction
    4. Groq LLM generation

    Returns the answer with source attribution and token usage.
    """
    if _pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Pipeline is still loading. Please retry in a few seconds.",
        )

    t0 = time.time()
    log.info(f"[{req.session_id[:8]}] Query: {req.query!r}")

    try:
        result = _pipeline.run(req.query, debug=req.debug)
    except Exception as e:
        log.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your query: {str(e)}",
        )

    elapsed_ms = int((time.time() - t0) * 1000)
    log.info(
        f"[{req.session_id[:8]}] Answered in {elapsed_ms}ms "
        f"({result['input_tokens']} in / {result['output_tokens']} out tokens)"
    )

    # Persist to in-memory session history
    history = _sessions.setdefault(req.session_id, [])
    history.append({"role": "user",      "content": req.query})
    history.append({"role": "assistant", "content": result["answer"]})

    return ChatResponse(
        answer           = result["answer"],
        query            = req.query,
        session_id       = req.session_id,
        source_funds     = result["source_funds"],
        source_sections  = result["source_sections"],
        source_urls      = result["source_urls"],
        num_chunks       = result["num_chunks"],
        context_summary  = result["context_summary"],
        model            = result["model"],
        input_tokens     = result["input_tokens"],
        output_tokens    = result["output_tokens"],
        response_time_ms = elapsed_ms,
        retrieved_chunks = result.get("retrieved_chunks") if req.debug else None,
        intent           = result.get("intent") if req.debug else None,
    )


@app.get(
    "/api/chat/history/{session_id}",
    response_model=HistoryResponse,
    summary="Get conversation history",
    tags=["Chat"],
)
async def get_history(session_id: str):
    """Returns the full conversation history for a session."""
    messages = _sessions.get(session_id, [])
    return HistoryResponse(
        session_id = session_id,
        messages   = messages,
        count      = len(messages),
    )


@app.delete(
    "/api/chat/history/{session_id}",
    summary="Clear conversation history",
    tags=["Chat"],
)
async def clear_history(session_id: str):
    """Clears all messages for a session."""
    if session_id in _sessions:
        del _sessions[session_id]
    return {"session_id": session_id, "cleared": True}


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({
        "name":    "HDFC Mutual Fund RAG API",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/api/health",
        "funds":   "/api/funds",
        "chat":    "POST /api/chat",
    })
