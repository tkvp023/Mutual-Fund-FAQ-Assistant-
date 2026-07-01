"""
Two-stage filtered retriever for the HDFC Mutual Fund RAG pipeline.

Stage 1: IntentDetector classifies the query → fund_filter + section_hints + top_k
Stage 2: ChromaDB filtered vector search (metadata pre-filter + cosine similarity)
Stage 3: Post-process: deduplicate, sort by distance, annotate with score
"""

from embeddings.embedder import BGEEmbedder
from vectorstore.store import VectorStore
from retriever.intent_detector import IntentDetector
from config.settings import TOP_K, EMBEDDING_MODEL, EMBEDDING_DEVICE, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME


class FundRetriever:
    """
    Two-stage retriever with intent-based metadata pre-filtering.

    Why two stages?
    - All 5 fund names share the "HDFC ... Direct Growth" prefix.
      Pure vector search on "What is the expense ratio?" returns chunks
      from all 5 funds with nearly identical cosine scores.
    - Pre-filtering by fund_name + section scopes the search BEFORE
      the vector comparison, making retrieval precise and fast.
    - Fallback to unfiltered search ensures robustness when filters
      are too restrictive (< 2 results).
    """

    def __init__(self):
        self.embedder = BGEEmbedder(
            model_name=EMBEDDING_MODEL,
            device=EMBEDDING_DEVICE,
        )
        self.store    = VectorStore(
            collection_name=CHROMA_COLLECTION_NAME,
            persist_dir=CHROMA_PERSIST_DIR,
        )
        self.detector = IntentDetector()
        self.default_top_k = TOP_K

    def retrieve(self, query: str, debug: bool = False):
        """
        Retrieve the most relevant chunks for a user query.

        Args:
            query: User's natural language question.
            debug: If True, returns (chunks, intent_dict) instead of just chunks.

        Returns:
            List of chunk dicts ordered by relevance (lowest distance first):
                content:  str    — the chunk text
                metadata: dict   — fund_name, section, chunk_type, ...
                distance: float  — cosine distance (0 = identical, 2 = opposite)
                score:    float  — cosine similarity = 1 - distance (1 = perfect)
        """
        # ── Stage 1: Detect intent ────────────────────────────────────────────
        intent = self.detector.detect(query)
        top_k  = intent["top_k"]

        # ── Stage 2: Build where-filter and embed query ───────────────────────
        where = self._build_filter(intent)
        q_vec = self.embedder.embed_query(query)

        # ── Stage 3: Filtered vector search ──────────────────────────────────
        results = self.store.query(
            q_vec,
            n_results=top_k,
            where=where if where else None,
        )
        chunks = self._parse_results(results)

        # Fallback: widen to no filter if too few results
        if len(chunks) < 2:
            results = self.store.query(q_vec, n_results=self.default_top_k)
            chunks  = self._parse_results(results)

        # ── Stage 4: Post-process ─────────────────────────────────────────────
        chunks = self._deduplicate(chunks)
        chunks.sort(key=lambda x: x["distance"])

        if debug:
            return chunks, intent
        return chunks

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_filter(self, intent: dict) -> dict | None:
        """
        Compose a ChromaDB where= filter from intent signals.

        Logic:
          - If exactly one fund is named AND query is not comparative:
            add fund_name filter (reduces search from 128 → ~31 chunks)
          - If primary section is highly specific (single section hint) AND not comparative:
            add section filter too
          - Otherwise: no filter (full corpus search)
        """
        fund_filter   = intent.get("fund_filter")
        section_hints = intent.get("section_hints", [])
        is_comparative = intent.get("is_comparative", False)

        conditions = []

        if fund_filter and not is_comparative:
            conditions.append({"fund_name": {"$eq": fund_filter}})

        # Apply section filter only when single, specific section is targeted
        if len(section_hints) == 1 and not is_comparative:
            conditions.append({"section": {"$eq": section_hints[0]}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _parse_results(self, results: dict) -> list[dict]:
        """Convert raw ChromaDB query result into clean chunk dicts."""
        chunks = []
        docs  = results.get("documents",  [[]])[0]
        metas = results.get("metadatas",  [[]])[0]
        dists = results.get("distances",  [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            chunks.append({
                "content":  doc,
                "metadata": meta,
                "distance": round(float(dist), 6),
                "score":    round(1.0 - float(dist), 4),  # cosine similarity
            })
        return chunks

    def _deduplicate(self, chunks: list[dict]) -> list[dict]:
        """Remove exact duplicate chunks (same fund_slug + section + chunk_index)."""
        seen, unique = set(), []
        for c in chunks:
            m   = c["metadata"]
            key = (m.get("fund_slug"), m.get("section"), m.get("chunk_index"))
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique
