"""
Phase 2 Tests — Chunker, Embedder, and Vector Store

Tests the SectionAwareChunker output, BGE embedding dimensions,
and ChromaDB storage/retrieval.

Run:
    pytest tests/test_phase2.py -v
"""

import os
import sys
import json
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

CHUNKS_PATH = os.path.join(ROOT, "data", "chunks", "all_chunks.json")
MID_CAP_CHUNKS_PATH = os.path.join(ROOT, "data", "chunks", "hdfc-mid-cap-fund-direct-growth_chunks.json")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def all_chunks():
    if not os.path.exists(CHUNKS_PATH):
        pytest.skip("all_chunks.json not found. Run scripts/run_phase2.py first.")
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def mid_cap_chunks():
    if not os.path.exists(MID_CAP_CHUNKS_PATH):
        pytest.skip("Mid Cap chunks file not found.")
    with open(MID_CAP_CHUNKS_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def embedder():
    from embeddings.embedder import BGEEmbedder
    return BGEEmbedder()


@pytest.fixture(scope="module")
def store():
    from vectorstore.store import VectorStore
    s = VectorStore()
    if s.count() == 0:
        pytest.skip("ChromaDB is empty. Run python -m pipeline.ingest first.")
    return s


# ── 2.1: SectionAwareChunker Tests ───────────────────────────────────────────

class TestSectionAwareChunker:

    def test_total_chunk_count(self, all_chunks):
        """Total chunk count matches expected 128 across 5 funds."""
        assert len(all_chunks) == 128, f"Expected 128 chunks, got {len(all_chunks)}"

    def test_mid_cap_chunk_count(self, mid_cap_chunks):
        """Mid Cap fund has exactly 31 chunks."""
        assert len(mid_cap_chunks) == 31, f"Expected 31 Mid Cap chunks, got {len(mid_cap_chunks)}"

    def test_all_sections_present(self, mid_cap_chunks):
        """All expected section types appear in Mid Cap chunks."""
        sections = {c["metadata"]["section"] for c in mid_cap_chunks}
        expected = {
            "overview", "returns", "holdings", "exit_load_tax",
            "investment_info", "performance_ranking", "fund_management",
            "about_fund", "fund_house", "faq",
        }
        missing = expected - sections
        assert not missing, f"Missing sections: {missing}"

    def test_overview_chunk_content(self, mid_cap_chunks):
        """Overview chunk contains all key facts."""
        overview = next(
            (c for c in mid_cap_chunks if c["metadata"]["section"] == "overview"), None
        )
        assert overview is not None, "No overview chunk found"
        content = overview["content"]
        assert "NAV" in content
        assert "AUM" in content
        assert "Expense Ratio" in content
        assert "Mid Cap" in content
        assert "HDFC Mid Cap Fund" in content

    def test_returns_chunk_content(self, mid_cap_chunks):
        """Returns chunk contains period labels and percentage values."""
        returns = next(
            (c for c in mid_cap_chunks if c["metadata"]["section"] == "returns"), None
        )
        assert returns is not None, "No returns chunk found"
        content = returns["content"]
        assert "1Y" in content or "1y" in content or "1M" in content
        assert "%" in content
        assert "Annualised" in content

    def test_faq_chunks_are_plain_text(self, mid_cap_chunks):
        """FAQ chunks contain no raw HTML tags."""
        faq_chunks = [c for c in mid_cap_chunks if c["metadata"]["section"] == "faq"]
        assert len(faq_chunks) == 8, f"Expected 8 FAQ chunks, got {len(faq_chunks)}"
        for chunk in faq_chunks:
            content = chunk["content"]
            assert "<p>" not in content, f"HTML <p> in FAQ chunk: {content[:80]}"
            assert "<ul>" not in content
            assert "Q:" in content
            assert "A:" in content

    def test_holdings_chunks_sector_grouped(self, mid_cap_chunks):
        """Holdings chunks have sector info in headers."""
        holdings = [c for c in mid_cap_chunks if c["metadata"]["section"] == "holdings"]
        assert len(holdings) > 0, "No holdings chunks found"
        for chunk in holdings:
            content = chunk["content"]
            assert "Portfolio Holdings" in content
            assert "HDFC Mid Cap" in content

    def test_chunk_metadata_schema(self, all_chunks):
        """Every chunk has the required metadata fields."""
        required_fields = ["fund_name", "fund_slug", "section", "chunk_type", "chunk_index", "source_url"]
        for chunk in all_chunks:
            meta = chunk["metadata"]
            for field in required_fields:
                assert field in meta, f"Missing metadata field '{field}' in chunk: {meta}"
            assert meta["fund_name"], "fund_name should not be empty"
            assert meta["section"], "section should not be empty"

    def test_chunk_ids_unique(self, all_chunks):
        """Chunk IDs (slug + section + index) are unique — no duplicates."""
        ids = []
        for c in all_chunks:
            m = c["metadata"]
            ids.append(f"{m['fund_slug']}__{m['section']}__{m['chunk_index']}")
        assert len(ids) == len(set(ids)), "Duplicate chunk IDs detected"

    def test_no_empty_chunks(self, all_chunks):
        """No chunk has empty content."""
        for chunk in all_chunks:
            assert chunk["content"].strip(), f"Empty chunk: {chunk['metadata']}"

    def test_chunks_per_fund(self, all_chunks):
        """Each fund has the expected chunk count."""
        from collections import Counter
        fund_counts = Counter(c["metadata"]["fund_name"] for c in all_chunks)
        # Gold and Silver ETF FoF have fewer holdings → 18 chunks each
        # Mid Cap, Large Cap, Small Cap have more holdings → 30-31 chunks each
        assert fund_counts["HDFC Gold ETF Fund of Fund Direct Plan Growth"] == 18
        assert fund_counts["HDFC Silver ETF FoF Direct Growth"] == 18
        assert fund_counts["HDFC Mid Cap Fund Direct Growth"] == 31
        assert fund_counts["HDFC Small Cap Fund Direct Growth"] == 31


# ── 2.2: BGE Embedder Tests ───────────────────────────────────────────────────

class TestBGEEmbedder:

    def test_model_loads(self, embedder):
        """BGEEmbedder loads without error."""
        assert embedder is not None
        assert embedder.dimensions == 384

    def test_embed_documents_shape(self, embedder):
        """embed_documents returns correct shape."""
        texts = [
            "HDFC Mid Cap Fund NAV is Rs.226.92",
            "Expense ratio is 0.75%",
        ]
        vectors = embedder.embed_documents(texts)
        assert len(vectors) == 2
        assert len(vectors[0]) == 384
        assert len(vectors[1]) == 384

    def test_embed_query_shape(self, embedder):
        """embed_query returns a 384-dim vector."""
        vec = embedder.embed_query("What is the NAV of HDFC Mid Cap Fund?")
        assert isinstance(vec, list)
        assert len(vec) == 384

    def test_embeddings_are_normalized(self, embedder):
        """Vectors are L2-normalized (norm ≈ 1.0) due to normalize_embeddings=True."""
        import math
        vec = embedder.embed_query("HDFC Mid Cap Fund expense ratio")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01, f"Vector norm {norm:.4f} is not close to 1.0"

    def test_similar_queries_closer_than_random(self, embedder):
        """Semantically similar texts have smaller cosine distance than random."""
        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        nav_q  = embedder.embed_query("What is the NAV of HDFC Mid Cap Fund?")
        nav_doc = embedder.embed_query("NAV of HDFC Mid Cap Fund Direct Growth is Rs.226.92")
        unrelated = embedder.embed_query("What is the weather in Mumbai today?")

        sim_nav  = dot(nav_q, nav_doc)    # should be high (similar topics)
        sim_unrelated = dot(nav_q, unrelated)  # should be lower

        assert sim_nav > sim_unrelated, (
            f"NAV similarity ({sim_nav:.4f}) should be higher than unrelated ({sim_unrelated:.4f})"
        )

    def test_batch_embedding_consistency(self, embedder):
        """Batch and single embedding return same result."""
        text = "HDFC Small Cap Fund 5Y returns are 20.87%"
        single = embedder.embed_documents([text])[0]
        batch  = embedder.embed_documents([text, "filler text"])[0]
        # Vectors should be identical
        diffs = [abs(a - b) for a, b in zip(single, batch)]
        assert max(diffs) < 1e-5, "Batch and single embeddings differ"


# ── 2.3: Vector Store (ChromaDB) Tests ────────────────────────────────────────

class TestVectorStore:

    def test_count_matches_chunks(self, store):
        """ChromaDB has exactly 128 stored chunks."""
        assert store.count() == 128, f"Expected 128 chunks, got {store.count()}"

    def test_collection_info_structure(self, store):
        """collection_info() returns correct structure."""
        info = store.collection_info()
        assert info["total"] == 128
        assert len(info["funds"]) == 5
        assert "HDFC Mid Cap Fund Direct Growth" in info["funds"]
        assert "overview" in info["sections"]
        assert "faq" in info["sections"]
        assert "holdings" in info["sections"]

    def test_basic_vector_query(self, store, embedder):
        """Vector query returns results with correct structure."""
        q_vec = embedder.embed_query("NAV of HDFC Mid Cap Fund")
        results = store.query(q_vec, n_results=3)
        assert "documents" in results
        assert "metadatas" in results
        assert "distances" in results
        assert len(results["documents"][0]) == 3

    def test_fund_name_filter(self, store, embedder):
        """Metadata filter by fund_name returns only that fund's chunks."""
        q_vec = embedder.embed_query("expense ratio")
        results = store.query(
            q_vec,
            n_results=3,
            where={"fund_name": {"$eq": "HDFC Mid Cap Fund Direct Growth"}},
        )
        for meta in results["metadatas"][0]:
            assert meta["fund_name"] == "HDFC Mid Cap Fund Direct Growth", (
                f"Filter leakage: got {meta['fund_name']}"
            )

    def test_section_filter(self, store, embedder):
        """Metadata filter by section returns only that section's chunks."""
        q_vec = embedder.embed_query("returns performance")
        results = store.query(
            q_vec,
            n_results=5,
            where={"section": {"$eq": "returns"}},
        )
        for meta in results["metadatas"][0]:
            assert meta["section"] == "returns", (
                f"Filter leakage: got section={meta['section']}"
            )

    def test_combined_filter(self, store, embedder):
        """Combined fund_name + section filter works correctly."""
        q_vec = embedder.embed_query("NAV AUM expense")
        results = store.query(
            q_vec,
            n_results=3,
            where={"$and": [
                {"fund_name": {"$eq": "HDFC Mid Cap Fund Direct Growth"}},
                {"section": {"$eq": "overview"}},
            ]},
        )
        assert len(results["documents"][0]) >= 1
        for meta in results["metadatas"][0]:
            assert meta["fund_name"] == "HDFC Mid Cap Fund Direct Growth"
            assert meta["section"] == "overview"

    def test_distances_are_valid_cosine(self, store, embedder):
        """All returned distances are valid cosine distances [0, 2]."""
        q_vec = embedder.embed_query("HDFC fund information")
        results = store.query(q_vec, n_results=10)
        for dist in results["distances"][0]:
            assert 0.0 <= dist <= 2.0, f"Invalid cosine distance: {dist}"

    def test_nav_query_top_result(self, store, embedder):
        """NAV query for Mid Cap returns Mid Cap chunk as top result."""
        q_vec = embedder.embed_query("What is the NAV of HDFC Mid Cap Fund Direct Growth?")
        results = store.query(q_vec, n_results=3)
        top_fund = results["metadatas"][0][0]["fund_name"]
        assert "Mid Cap" in top_fund, f"Top result is from wrong fund: {top_fund}"

    def test_returns_query_top_result(self, store, embedder):
        """Returns query for Small Cap returns Small Cap returns chunk."""
        q_vec = embedder.embed_query("3Y returns of HDFC Small Cap Fund")
        results = store.query(q_vec, n_results=3)
        top_fund = results["metadatas"][0][0]["fund_name"]
        assert "Small Cap" in top_fund, f"Top result is from wrong fund: {top_fund}"
