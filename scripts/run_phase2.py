"""
Phase 2 Runner — Re-extract + Chunk

This script:
  1. Re-extracts structured data from the already-scraped HTML files
     (using the fixed ContentExtractor that reads __NEXT_DATA__ JSON)
  2. Chunks all documents using SectionAwareChunker
  3. Saves chunks to data/chunks/ for inspection

Usage:
  python scripts/run_phase2.py
"""

import sys
import io
import os
import json
from datetime import datetime

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from extractor.content_extractor import ContentExtractor
from chunker.text_chunker import SectionAwareChunker


def load_html_from_disk(raw_html_dir: str = "data/raw_html") -> dict:
    """Load previously scraped HTML files from disk."""
    html_results = {}
    for fname in os.listdir(raw_html_dir):
        if not fname.endswith(".html"):
            continue
        fpath = os.path.join(raw_html_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            html = f.read()
        # Reconstruct URL from slug
        slug = fname.replace(".html", "")
        url = f"https://groww.in/mutual-funds/{slug}"
        html_results[url] = html
    return html_results


def run_phase2():
    start_time = datetime.now()

    print("=" * 70)
    print("  PHASE 2: Re-Extract + Section-Aware Chunking")
    print("=" * 70)
    print(f"\n  Start time: {start_time.isoformat()}")

    # ── Step 1: Load HTML ──────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("  STEP 1: Loading scraped HTML from disk")
    print("-" * 70 + "\n")

    html_results = load_html_from_disk("data/raw_html")
    print(f"  Loaded {len(html_results)} HTML files")
    for url in html_results:
        print(f"    * {url.split('/')[-1]}")

    # ── Step 2: Re-Extract (fixed extractor) ────────────────────────────────
    print("\n" + "-" * 70)
    print("  STEP 2: Extracting structured data (via __NEXT_DATA__ JSON)")
    print("-" * 70 + "\n")

    extractor = ContentExtractor()
    documents = extractor.extract_all(html_results)

    # Save extracted data (overwrites old data/extracted/)
    print("\n  Saving extracted data...")
    extractor.save_extracted_data(documents, output_dir="data/extracted")

    # ── Step 3: Chunk ───────────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("  STEP 3: Chunking with SectionAwareChunker")
    print("-" * 70 + "\n")

    chunker = SectionAwareChunker()
    all_chunks = chunker.chunk_all(documents)
    print(f"\n  Total chunks across all funds: {len(all_chunks)}")

    # Per-fund breakdown
    from collections import Counter
    fund_counts = Counter(c["metadata"]["fund_name"] for c in all_chunks)
    section_counts = Counter(c["metadata"]["section"] for c in all_chunks)

    print("\n  Chunks per fund:")
    for fund, count in fund_counts.items():
        print(f"    {count:3d}  {fund}")

    print("\n  Chunks per section type:")
    for sec, count in sorted(section_counts.items(), key=lambda x: -x[1]):
        print(f"    {count:3d}  {sec}")

    # ── Save chunks ──────────────────────────────────────────────────────────
    chunks_dir = "data/chunks"
    os.makedirs(chunks_dir, exist_ok=True)

    # Save all chunks as JSON
    all_chunks_path = os.path.join(chunks_dir, "all_chunks.json")
    with open(all_chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved {len(all_chunks)} chunks → {all_chunks_path}")

    # Save readable text dump for inspection
    readable_path = os.path.join(chunks_dir, "chunks_readable.txt")
    with open(readable_path, "w", encoding="utf-8") as f:
        f.write(f"Total chunks: {len(all_chunks)}\n")
        f.write("=" * 80 + "\n\n")
        for i, chunk in enumerate(all_chunks):
            meta = chunk["metadata"]
            f.write(f"--- Chunk {i+1} | {meta['fund_name']} | section: {meta['section']} | type: {meta['chunk_type']} ---\n")
            f.write(chunk["content"])
            f.write("\n\n")
    print(f"  Saved readable dump → {readable_path}")

    # Per-fund chunk files
    from itertools import groupby
    by_fund = {}
    for chunk in all_chunks:
        slug = chunk["metadata"]["fund_slug"]
        by_fund.setdefault(slug, []).append(chunk)

    for slug, fund_chunks in by_fund.items():
        fpath = os.path.join(chunks_dir, f"{slug}_chunks.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(fund_chunks, f, indent=2, ensure_ascii=False)

    # ── Summary report ───────────────────────────────────────────────────────
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 70)
    print("  PHASE 2 COMPLETE!")
    print("=" * 70)
    print(f"\n  Duration:      {duration:.1f}s")
    print(f"  Documents:     {len(documents)}")
    print(f"  Total chunks:  {len(all_chunks)}")
    print(f"\n  Output:")
    print(f"    data/extracted/          ← fixed structured JSON")
    print(f"    data/extracted/sections/ ← per-fund section split text")
    print(f"    data/chunks/             ← chunk JSON + readable dump")

    # Save run report
    report = {
        "phase": "Phase 2: Re-Extract + Chunk",
        "timestamp": end_time.isoformat(),
        "duration_seconds": round(duration, 1),
        "documents": len(documents),
        "total_chunks": len(all_chunks),
        "chunks_per_fund": dict(fund_counts),
        "chunks_per_section": dict(section_counts),
        "documents_detail": [
            {
                "fund_name":     doc["fund_name"],
                "nav":           doc["nav"],
                "nav_date":      doc["nav_date"],
                "aum_cr":        doc["aum_cr"],
                "expense_ratio": doc["expense_ratio"],
                "holdings":      len(doc["holdings"]),
                "faq":           len(doc["faq"]),
                "returns":       doc["returns_annualised"],
            }
            for doc in documents
        ],
    }
    report_path = "data/phase2_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"    {report_path}           ← run report")


if __name__ == "__main__":
    run_phase2()
