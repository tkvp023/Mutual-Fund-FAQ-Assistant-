"""
Section-aware chunker for Groww mutual fund documents.

Each section type gets a dedicated chunking strategy based on its
structure and RAG retrieval value. The chunker works from the
structured `doc` dict produced by ContentExtractor.
"""

from datetime import datetime
from chunker.preprocessor import (
    build_overview_chunk,
    build_about_chunk,
    build_returns_chunk,
    build_exit_load_tax_chunk,
    build_investment_info_chunk,
    build_holdings_chunks,
    build_fund_management_chunks,
    build_performance_ranking_chunk,
    build_peer_comparison_chunk,
    build_fund_house_chunk,
    build_faq_chunks,
)


class SectionAwareChunker:
    """
    Converts a ContentExtractor document dict into a flat list of
    chunk dicts ready for embedding and storage in ChromaDB.

    Chunk format:
        {
            "content":  str,          # the text to embed
            "metadata": {
                "fund_name":    str,
                "fund_slug":    str,
                "source_url":   str,
                "section":      str,  # section type
                "chunk_type":   str,  # fine-grained type
                "chunk_index":  int,  # position within fund
                "scraped_at":   str,
                # optional extra fields (holdings_sector, manager_name, ...)
            }
        }
    """

    def chunk(self, doc: dict) -> list:
        """
        Produce all chunks for a single fund document.

        Args:
            doc: dict returned by ContentExtractor.extract()

        Returns:
            List of chunk dicts with 'content' and 'metadata'.
        """
        base_meta = {
            "fund_name":  doc["fund_name"],
            "fund_slug":  doc.get("fund_slug", ""),
            "source_url": doc["source_url"],
            "scraped_at": doc.get("scraped_at", ""),
        }

        raw_chunks = []   # list of (section, chunk_type, text, extra_meta)

        # ── 1. Overview (synthesised fund card) ──────────────────────────────
        text = build_overview_chunk(doc)
        if text.strip():
            raw_chunks.append(("overview", "overview_card", text, {}))

        # ── 2. About fund ────────────────────────────────────────────────────
        text = build_about_chunk(doc)
        if text.strip():
            raw_chunks.append(("about_fund", "about", text, {}))

        # ── 3. Returns ───────────────────────────────────────────────────────
        text = build_returns_chunk(doc)
        if text.strip():
            raw_chunks.append(("returns", "returns_table", text, {}))

        # ── 4. Exit load & tax ───────────────────────────────────────────────
        text = build_exit_load_tax_chunk(doc)
        if text.strip():
            raw_chunks.append(("exit_load_tax", "exit_load_tax", text, {}))

        # ── 5. Investment info ───────────────────────────────────────────────
        text = build_investment_info_chunk(doc)
        if text.strip():
            raw_chunks.append(("investment_info", "investment_info", text, {}))

        # ── 6. Performance vs category / rankings ────────────────────────────
        text = build_performance_ranking_chunk(doc)
        if text.strip():
            raw_chunks.append(("performance_ranking", "performance_ranking", text, {}))

        # ── 7. Peer comparison ───────────────────────────────────────────────
        text = build_peer_comparison_chunk(doc)
        if text.strip():
            raw_chunks.append(("peer_comparison", "peer_comparison", text, {}))

        # ── 8. Holdings (sector-batched) ─────────────────────────────────────
        for text, extra in build_holdings_chunks(doc, batch_size=10):
            if text.strip():
                raw_chunks.append(("holdings", extra.get("chunk_type", "holdings_batch"), text, extra))

        # ── 9. Fund management (per manager) ─────────────────────────────────
        for text, extra in build_fund_management_chunks(doc):
            if text.strip():
                raw_chunks.append(("fund_management", extra.get("chunk_type", "fund_manager"), text, extra))

        # ── 10. Fund house ───────────────────────────────────────────────────
        text = build_fund_house_chunk(doc)
        if text.strip():
            raw_chunks.append(("fund_house", "fund_house", text, {}))

        # ── 11. FAQ (one chunk per Q&A) ──────────────────────────────────────
        for text, extra in build_faq_chunks(doc):
            if text.strip():
                raw_chunks.append(("faq", extra.get("chunk_type", "faq"), text, extra))

        # ── Assemble final chunk dicts ────────────────────────────────────────
        chunks = []
        for idx, (section, chunk_type, content, extra) in enumerate(raw_chunks):
            meta = {
                **base_meta,
                "section":     section,
                "chunk_type":  chunk_type,
                "chunk_index": idx,
                **extra,
            }
            chunks.append({"content": content, "metadata": meta})

        return chunks

    def chunk_all(self, documents: list) -> list:
        """
        Chunk all documents in a list.

        Args:
            documents: List of dicts from ContentExtractor.extract_all()

        Returns:
            Flat list of all chunk dicts across all funds.
        """
        all_chunks = []
        for doc in documents:
            fund_chunks = self.chunk(doc)
            all_chunks.extend(fund_chunks)
            print(f"  [OK] {doc['fund_name']}: {len(fund_chunks)} chunks")
        return all_chunks
