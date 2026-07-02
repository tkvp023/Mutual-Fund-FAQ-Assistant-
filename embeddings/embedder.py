"""
BGE Embedding Generator.

Uses BAAI/bge-small-en-v1.5 (384-dim, ~33MB) for this project.

Model selection rationale (from data analysis):
  - Corpus: 128 chunks, avg 347 chars — short, dense, factual
  - BGE-small vs BGE-large MTEB gap: 62.17 vs 64.23 (2 pts) — negligible at this scale
  - CPU embed time: ~3-5s (small) vs ~25-40s (large) — 8-10x difference matters on refresh
  - Upgrade to bge-large when corpus exceeds ~1000 chunks or GPU is available
"""

from langchain_huggingface import HuggingFaceEmbeddings

# ── Model constants ──────────────────────────────────────────────────────────
RECOMMENDED_MODEL = "BAAI/bge-small-en-v1.5"

# BGE asymmetric retrieval: queries need an instruction prefix; documents do not.
# LangChain's HuggingFaceBgeEmbeddings applies this automatically to embed_query().
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class BGEEmbedder:
    """
    BGE embedding wrapper for the RAG pipeline.

    Chosen model: BAAI/bge-small-en-v1.5 (384-dim)
      - normalize_embeddings=True  → cosine similarity via dot product
      - Asymmetric retrieval       → query prefix applied automatically
      - Batch embedding            → controls memory for larger corpora
    """

    def __init__(
        self,
        model_name: str = RECOMMENDED_MODEL,
        device: str = "cpu",
    ):
        """
        Load the BGE model.

        Args:
            model_name: HuggingFace model ID. Default: BAAI/bge-small-en-v1.5.
                        Upgrade to BAAI/bge-large-en-v1.5 if corpus > 1000 chunks.
            device:     'cpu' or 'cuda'. Auto-detected if not set.
        """
        self.model_name = model_name
        self.device = device
        print(f"  Loading BGE model: {model_name} (device={device})...")
        self.model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},  # enables cosine via dot product
        )
        print(f"  Model loaded. Dimensions: {self.dimensions}")

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Embed a list of document chunks in batches.

        Documents are embedded WITHOUT the query instruction prefix
        (BGE asymmetric retrieval design).

        Args:
            texts:      List of chunk content strings.
            batch_size: Process this many chunks at once (controls RAM peak).

        Returns:
            List of float vectors, one per input text.
            Shape: (len(texts), self.dimensions)
        """
        all_embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i: i + batch_size]
            batch_embeddings = self.model.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
            done = min(i + batch_size, total)
            print(f"    Embedded {done}/{total} chunks...", end="\r")

        print(f"    Embedded {total}/{total} chunks. Done.     ")
        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single user query.

        The query instruction prefix is applied automatically by
        HuggingFaceBgeEmbeddings for asymmetric retrieval.

        Args:
            query: The user's natural language question.

        Returns:
            Float vector of shape (self.dimensions,).
        """
        return self.model.embed_query(query)

    @property
    def dimensions(self) -> int:
        """Embedding dimensions: 384 for bge-small, 1024 for bge-large."""
        return 384 if "small" in self.model_name else 1024
