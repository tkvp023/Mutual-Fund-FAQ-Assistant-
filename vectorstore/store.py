"""
ChromaDB Vector Store for the HDFC Mutual Fund RAG pipeline.

Uses cosine similarity (hnsw:space = cosine) with persistent storage.
Chunk metadata (fund_name, section, chunk_type) enables pre-filtering
at query time to reduce disambiguation burden on the embedding model.
"""

import chromadb
from chromadb.config import Settings
import os


class VectorStore:
    """
    ChromaDB-backed vector store for fund chunks.

    Design decisions:
      - hnsw:space = cosine  : matches normalize_embeddings=True from BGEEmbedder
      - PersistentClient     : survives process restarts; no re-ingestion needed
      - Metadata pre-filter  : query can filter by fund_name / section / chunk_type
        before vector search, reducing false-positive retrievals across similar funds
    """

    def __init__(
        self,
        collection_name: str = "hdfc_funds",
        persist_dir: str = "./chroma_db",
    ):
        """
        Connect to (or create) a ChromaDB collection.

        Args:
            collection_name: Name of the ChromaDB collection.
            persist_dir:     Directory to persist the database.
        """
        os.makedirs(persist_dir, exist_ok=True)
        self.collection_name = collection_name
        self.persist_dir = persist_dir

        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # dot product on normalized vecs = cosine sim
        )

    # ── Write ─────────────────────────────────────────────────────────────────

    def add_documents(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """
        Add chunk documents + precomputed embeddings to the collection.

        Args:
            chunks:     List of chunk dicts with 'content' and 'metadata' keys.
            embeddings: Corresponding embedding vectors (from BGEEmbedder).
        """
        assert len(chunks) == len(embeddings), (
            f"Chunk count ({len(chunks)}) != embedding count ({len(embeddings)})"
        )

        # Build stable chunk IDs: slug + section + chunk_index
        ids = []
        for c in chunks:
            meta = c["metadata"]
            slug  = meta.get("fund_slug", "unknown")
            sec   = meta.get("section", "misc")
            idx   = meta.get("chunk_index", 0)
            ids.append(f"{slug}__{sec}__{idx}")

        self.collection.add(
            ids=ids,
            documents=[c["content"] for c in chunks],
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in chunks],
        )

    # ── Read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict | None = None,
    ) -> dict:
        """
        Retrieve the top-n most similar chunks.

        Args:
            query_embedding: Embedded query vector (from BGEEmbedder.embed_query).
            n_results:       Number of chunks to return.
            where:           Optional ChromaDB metadata filter dict.
                             e.g. {"fund_name": "HDFC Mid Cap Fund Direct Growth"}
                             e.g. {"section": {"$in": ["overview", "returns"]}}

        Returns:
            ChromaDB query result dict with keys:
              ids, documents, metadatas, distances, embeddings
        """
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        return self.collection.query(**kwargs)

    def get_by_section(self, fund_slug: str, section: str) -> dict:
        """
        Retrieve all chunks for a specific fund + section (exact match).
        Useful for debugging retrieval quality per section.
        """
        return self.collection.get(
            where={"$and": [
                {"fund_slug": fund_slug},
                {"section": section},
            ]},
            include=["documents", "metadatas"],
        )

    # ── Utility ───────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Return total number of chunks stored in the collection."""
        return self.collection.count()

    def reset(self) -> None:
        """
        Delete and recreate the collection (use before re-ingestion).
        This is safe — all data is re-embedded from the chunks JSON.
        """
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"  Collection '{self.collection_name}' reset (empty).")

    def collection_info(self) -> dict:
        """Return a summary of what's stored in the collection."""
        total = self.count()
        if total == 0:
            return {"total": 0, "funds": [], "sections": []}

        # Sample metadata to get fund/section breakdown
        sample = self.collection.get(
            limit=total,
            include=["metadatas"],
        )
        metas = sample["metadatas"]

        funds = list(set(m.get("fund_name", "") for m in metas))
        sections = list(set(m.get("section", "") for m in metas))
        chunk_types = list(set(m.get("chunk_type", "") for m in metas))

        from collections import Counter
        section_counts = Counter(m.get("section", "") for m in metas)
        fund_counts = Counter(m.get("fund_name", "") for m in metas)

        return {
            "total":          total,
            "funds":          sorted(funds),
            "fund_counts":    dict(fund_counts),
            "sections":       sorted(sections),
            "section_counts": dict(section_counts),
            "chunk_types":    sorted(chunk_types),
        }
