"""
Ingestion Pipeline Orchestrator.

Reads pre-computed chunks from data/chunks/all_chunks.json,
embeds them with BGE, and stores them in ChromaDB.

Does NOT re-scrape or re-extract by default — the HTML is already
saved in data/raw_html/ and chunks in data/chunks/.

To force a full re-extract + re-chunk before ingesting, set
REEXTRACT=True or pass --reextract on the CLI.

Usage:
    python -m pipeline.ingest          # embed + store existing chunks
    python -m pipeline.ingest --reset  # wipe ChromaDB, re-embed, re-store
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add project root so we can import our modules
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from embeddings.embedder import BGEEmbedder
from vectorstore.store import VectorStore
from config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_DEVICE,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
)


# ── Paths ─────────────────────────────────────────────────────────────────────
_CHUNKS_PATH    = os.path.join(_project_root, "data", "chunks", "all_chunks.json")
_LAST_RUN_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_ingestion")
_GUARD_HOURS    = 20  # Minimum hours between ingestion runs


# ── Ingestion guard ───────────────────────────────────────────────────────────
def is_ingestion_needed() -> bool:
    """Check if ingestion should run (not run in last 20 hours)."""
    if not os.path.exists(_LAST_RUN_FILE):
        return True
    try:
        with open(_LAST_RUN_FILE) as f:
            last_run = datetime.fromisoformat(f.read().strip())
        hours_since = (datetime.now() - last_run).total_seconds() / 3600
        return hours_since >= _GUARD_HOURS
    except (ValueError, OSError):
        return True  # Corrupted file — allow re-run


def mark_ingestion_complete():
    """Record the timestamp of successful ingestion."""
    with open(_LAST_RUN_FILE, "w") as f:
        f.write(datetime.now().isoformat())


def load_chunks(chunks_path: str = _CHUNKS_PATH) -> list[dict]:
    """Load pre-computed chunks from JSON file."""
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(
            f"Chunks file not found: {chunks_path}\n"
            "Run `python scripts/run_phase2.py` first to generate chunks."
        )
    with open(chunks_path, encoding="utf-8") as f:
        chunks = json.load(f)
    return chunks


def run_ingestion(
    reset: bool = True,
    chunks_path: str = _CHUNKS_PATH,
) -> dict:
    """
    Full ingestion: load chunks → embed → store in ChromaDB.

    Args:
        reset:       If True, wipe the ChromaDB collection before ingesting.
                     Set False to append (not recommended for re-runs).
        chunks_path: Path to the all_chunks.json file.

    Returns:
        Summary dict with timing and counts.
    """
    start = datetime.now()

    print("=" * 70)
    print("  INGESTION PIPELINE (Phase 2.3–2.4)")
    print("=" * 70)
    print(f"\n  Start time:  {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Embed model: {EMBEDDING_MODEL}")
    print(f"  ChromaDB:    {CHROMA_PERSIST_DIR}/{CHROMA_COLLECTION_NAME}")

    # ── Step 1: Load chunks ─────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("  STEP 1: Loading chunks from disk")
    print("-" * 70)

    chunks = load_chunks(chunks_path)
    print(f"\n  Loaded {len(chunks)} chunks from {chunks_path}")

    # Per-fund breakdown
    from collections import Counter
    fund_counts = Counter(c["metadata"]["fund_name"] for c in chunks)
    section_counts = Counter(c["metadata"]["section"] for c in chunks)

    print("\n  Chunks per fund:")
    for fund, count in fund_counts.items():
        print(f"    {count:3d}  {fund}")
    print("\n  Chunks per section:")
    for sec, count in sorted(section_counts.items(), key=lambda x: -x[1]):
        print(f"    {count:3d}  {sec}")

    # ── Step 2: Embed ────────────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("  STEP 2: Generating BGE embeddings")
    print("-" * 70 + "\n")

    embedder = BGEEmbedder(
        model_name=EMBEDDING_MODEL,
        device=EMBEDDING_DEVICE,
    )

    texts = [c["content"] for c in chunks]
    print(f"\n  Embedding {len(texts)} chunks (batch_size=32)...")
    embed_start = datetime.now()
    embeddings = embedder.embed_documents(texts, batch_size=32)
    embed_time = (datetime.now() - embed_start).total_seconds()

    print(f"\n  Embedding complete.")
    print(f"    Vectors:    {len(embeddings)} × {embedder.dimensions} dims")
    print(f"    Time:       {embed_time:.1f}s")
    print(f"    Storage est: {len(embeddings) * embedder.dimensions * 4 / 1024:.1f} KB")

    # Sanity check
    assert len(embeddings) == len(chunks), "Embedding count mismatch!"
    assert len(embeddings[0]) == embedder.dimensions, "Dimension mismatch!"

    # ── Step 3: Store in ChromaDB ────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("  STEP 3: Storing in ChromaDB")
    print("-" * 70 + "\n")

    store = VectorStore(
        collection_name=CHROMA_COLLECTION_NAME,
        persist_dir=CHROMA_PERSIST_DIR,
    )

    if reset:
        print("  Resetting collection (wipe + recreate)...")
        store.reset()

    print(f"  Adding {len(chunks)} documents to collection '{CHROMA_COLLECTION_NAME}'...")
    store.add_documents(chunks, embeddings)

    total_stored = store.count()
    print(f"  Stored: {total_stored} chunks in ChromaDB")
    assert total_stored == len(chunks), (
        f"Storage mismatch: stored {total_stored}, expected {len(chunks)}"
    )

    # Collection info
    info = store.collection_info()
    print(f"\n  Collection summary:")
    print(f"    Total chunks:  {info['total']}")
    print(f"    Funds indexed: {len(info['funds'])}")
    for fund in info["funds"]:
        print(f"      * {fund} ({info['fund_counts'].get(fund, '?')} chunks)")

    # ── Quick retrieval smoke test ────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("  STEP 4: Smoke test — 3 sample queries")
    print("-" * 70 + "\n")

    test_queries = [
        ("NAV query",      "What is the NAV of HDFC Mid Cap Fund?"),
        ("Returns query",  "What are the 3Y returns of HDFC Small Cap Fund?"),
        ("Expense query",  "Expense ratio of HDFC Gold ETF Fund of Fund?"),
    ]

    for label, query in test_queries:
        q_vec = embedder.embed_query(query)
        results = store.query(q_vec, n_results=3)
        top_doc = results["documents"][0][0][:80].replace("\n", " ")
        top_fund = results["metadatas"][0][0].get("fund_name", "?")
        top_sec  = results["metadatas"][0][0].get("section", "?")
        top_dist = results["distances"][0][0]

        print(f"  [{label}]")
        print(f"    Query:  '{query}'")
        print(f"    Top-1:  [{top_fund} | {top_sec}] dist={top_dist:.4f}")
        print(f"    Text:   '{top_doc}...'")
        print()

    # ── Summary ──────────────────────────────────────────────────────────────
    end = datetime.now()
    total_time = (end - start).total_seconds()

    print("=" * 70)
    print("  INGESTION COMPLETE [OK]")
    print("=" * 70)
    print(f"\n  Total time:    {total_time:.1f}s")
    print(f"  Embed time:    {embed_time:.1f}s")
    print(f"  Chunks stored: {total_stored}")
    print(f"  ChromaDB path: {os.path.abspath(CHROMA_PERSIST_DIR)}")
    print()

    return {
        "total_chunks":  total_stored,
        "embed_time_s":  round(embed_time, 1),
        "total_time_s":  round(total_time, 1),
        "collection":    CHROMA_COLLECTION_NAME,
        "persist_dir":   CHROMA_PERSIST_DIR,
        "funds":         info["funds"],
        "section_counts": info["section_counts"],
    }


def guarded_ingestion(
    force: bool = False,
    reset: bool = True,
    chunks_path: str = _CHUNKS_PATH,
) -> dict | None:
    """
    Run ingestion with a 20-hour guard to prevent double-runs.

    Args:
        force:       Bypass the guard and run anyway.
        reset:       Wipe ChromaDB before ingesting.
        chunks_path: Path to chunks JSON file.

    Returns:
        Summary dict if ingestion ran, None if skipped.
    """
    if not force and not is_ingestion_needed():
        try:
            with open(_LAST_RUN_FILE) as f:
                last_run = f.read().strip()
        except OSError:
            last_run = "unknown"
        print(f"⏭  Ingestion skipped — last run was at {last_run} "
              f"(less than {_GUARD_HOURS} hours ago).")
        print(f"   Use --force to override.")
        return None

    result = run_ingestion(reset=reset, chunks_path=chunks_path)
    mark_ingestion_complete()
    print(f"\n✓ Ingestion guard updated. Next run allowed after {_GUARD_HOURS} hours.")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest chunks into ChromaDB")
    parser.add_argument(
        "--reset",
        action="store_true",
        default=True,
        help="Wipe the ChromaDB collection before ingesting (default: True)",
    )
    parser.add_argument(
        "--no-reset",
        dest="reset",
        action="store_false",
        help="Append to existing collection instead of resetting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Bypass the 20-hour ingestion guard and run anyway",
    )
    parser.add_argument(
        "--chunks",
        default=_CHUNKS_PATH,
        help="Path to all_chunks.json (default: data/chunks/all_chunks.json)",
    )
    args = parser.parse_args()

    guarded_ingestion(force=args.force, reset=args.reset, chunks_path=args.chunks)
