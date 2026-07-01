"""
Phase 3 Tests — Intent Detector, Retriever, Prompt Builder, and Query Pipeline

Tests the full RAG query pipeline: intent classification, two-stage retrieval,
prompt construction, and end-to-end answer generation.

Run:
    pytest tests/test_phase3.py -v
    pytest tests/test_phase3.py -v -k "not TestQueryPipeline"  # skip LLM tests
"""

import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def detector():
    from retriever.intent_detector import IntentDetector
    return IntentDetector()


@pytest.fixture(scope="module")
def retriever():
    from vectorstore.store import VectorStore
    store = VectorStore()
    if store.count() == 0:
        pytest.skip("ChromaDB empty. Run python -m pipeline.ingest first.")
    from retriever.retriever import FundRetriever
    return FundRetriever()


@pytest.fixture(scope="module")
def pipeline():
    from config.settings import GROQ_API_KEY
    if not GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY not set. Set it in .env to run LLM tests.")
    from vectorstore.store import VectorStore
    store = VectorStore()
    if store.count() == 0:
        pytest.skip("ChromaDB empty. Run python -m pipeline.ingest first.")
    from pipeline.query import QueryPipeline
    return QueryPipeline()


# ── 3.1: IntentDetector Tests ─────────────────────────────────────────────────

class TestIntentDetector:

    def test_mid_cap_fund_detected(self, detector):
        """'mid cap' alias correctly resolves to full fund name."""
        result = detector.detect("What is the NAV of HDFC Mid Cap Fund?")
        assert result["fund_filter"] == "HDFC Mid Cap Fund Direct Growth"
        assert not result["is_comparative"]

    def test_gold_fund_detected(self, detector):
        """'gold etf' alias correctly resolves to Gold ETF FoF fund."""
        result = detector.detect("expense ratio of hdfc gold etf")
        assert "HDFC Gold ETF Fund of Fund Direct Plan Growth" in result["detected_funds"]

    def test_silver_fund_detected(self, detector):
        """'silver' alias resolves to Silver ETF FoF."""
        result = detector.detect("exit load of silver etf fund")
        assert "HDFC Silver ETF FoF Direct Growth" in result["detected_funds"]

    def test_nav_routes_to_overview(self, detector):
        """NAV keyword routes to overview section."""
        result = detector.detect("What is the NAV of HDFC Large Cap fund?")
        assert "overview" in result["section_hints"]

    def test_returns_routes_correctly(self, detector):
        """Returns keyword routes to returns section."""
        result = detector.detect("What are the 3Y returns of HDFC Mid Cap?")
        assert "returns" in result["section_hints"]

    def test_exit_load_routes_correctly(self, detector):
        """Exit load keyword routes to exit_load_tax section."""
        result = detector.detect("What is the exit load for HDFC Small Cap Fund?")
        assert "exit_load_tax" in result["section_hints"]

    def test_ltcg_routes_to_exit_load(self, detector):
        """LTCG keyword routes to exit_load_tax section."""
        result = detector.detect("What is LTCG tax on HDFC Large Cap redemption?")
        assert "exit_load_tax" in result["section_hints"]

    def test_holdings_routes_correctly(self, detector):
        """Holdings keyword routes to holdings section."""
        result = detector.detect("Top holdings of HDFC Small Cap Fund")
        assert "holdings" in result["section_hints"]

    def test_manager_routes_correctly(self, detector):
        """Fund manager keyword routes to fund_management section."""
        result = detector.detect("Who manages HDFC Mid Cap Fund?")
        assert "fund_management" in result["section_hints"]

    def test_sharpe_routes_to_performance(self, detector):
        """Sharpe ratio keyword routes to performance_ranking."""
        result = detector.detect("What is the Sharpe ratio of HDFC Mid Cap?")
        assert "performance_ranking" in result["section_hints"]

    def test_comparative_detected_via_keyword(self, detector):
        """'compare' keyword triggers comparative mode with top_k=5."""
        result = detector.detect("Compare returns of all HDFC funds")
        assert result["is_comparative"] is True
        assert result["top_k"] == 5

    def test_comparative_detected_via_vs(self, detector):
        """' vs ' keyword triggers comparative mode."""
        result = detector.detect("HDFC Mid Cap vs Small Cap 5Y returns")
        assert result["is_comparative"] is True
        assert result["fund_filter"] is None  # multiple funds → no single filter

    def test_two_funds_no_single_filter(self, detector):
        """Two fund aliases detected → fund_filter is None (no single filter)."""
        result = detector.detect("compare mid cap and large cap returns")
        assert result["fund_filter"] is None
        assert len(result["detected_funds"]) >= 2 or result["is_comparative"]

    def test_no_fund_no_filter(self, detector):
        """Generic query with no fund name → no fund_filter."""
        result = detector.detect("What is the expense ratio?")
        assert result["fund_filter"] is None

    def test_unknown_query_defaults_to_overview(self, detector):
        """Query with no keyword match defaults to overview section."""
        result = detector.detect("Tell me about this fund")
        assert len(result["section_hints"]) > 0  # has a fallback

    def test_top_k_single_fund_factual(self, detector):
        """Single-fund factual queries get top_k=3."""
        result = detector.detect("What is the AUM of HDFC Gold ETF?")
        assert result["top_k"] == 3


# ── 3.1: FundRetriever Tests ──────────────────────────────────────────────────

class TestFundRetriever:

    def test_retrieve_returns_list(self, retriever):
        """retrieve() returns a list of chunk dicts."""
        results = retriever.retrieve("What is the NAV of HDFC Mid Cap Fund?")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_chunk_structure(self, retriever):
        """Retrieved chunks have content, metadata, distance, score."""
        results = retriever.retrieve("expense ratio HDFC Large Cap")
        for r in results:
            assert "content" in r
            assert "metadata" in r
            assert "distance" in r
            assert "score" in r
            assert isinstance(r["content"], str)
            assert r["content"].strip(), "Chunk content should not be empty"

    def test_nav_query_correct_fund(self, retriever):
        """NAV query for Mid Cap returns Mid Cap chunks."""
        results = retriever.retrieve("What is the NAV of HDFC Mid Cap Fund?")
        top_fund = results[0]["metadata"]["fund_name"]
        assert "Mid Cap" in top_fund, f"Expected Mid Cap, got: {top_fund}"

    def test_returns_query_correct_fund(self, retriever):
        """Returns query for Small Cap returns Small Cap chunks."""
        results = retriever.retrieve("3Y and 5Y returns of HDFC Small Cap Fund")
        top_fund = results[0]["metadata"]["fund_name"]
        assert "Small Cap" in top_fund, f"Expected Small Cap, got: {top_fund}"

    def test_exit_load_query_correct_section(self, retriever):
        """Exit load query retrieves exit_load_tax section chunks."""
        results = retriever.retrieve("exit load of HDFC Mid Cap Fund")
        sections = [r["metadata"]["section"] for r in results]
        assert "exit_load_tax" in sections, f"exit_load_tax not in retrieved sections: {sections}"

    def test_holdings_query_correct_section(self, retriever):
        """Holdings query retrieves holdings section chunks."""
        results = retriever.retrieve("top holdings of HDFC Small Cap Fund")
        sections = [r["metadata"]["section"] for r in results]
        assert "holdings" in sections, f"holdings not in retrieved sections: {sections}"

    def test_sorted_by_distance(self, retriever):
        """Results are sorted by ascending distance (most relevant first)."""
        results = retriever.retrieve("NAV of HDFC Gold ETF Fund")
        distances = [r["distance"] for r in results]
        assert distances == sorted(distances), "Results not sorted by distance"

    def test_scores_are_valid(self, retriever):
        """All cosine scores are in [0, 1] range."""
        results = retriever.retrieve("HDFC fund expense ratio")
        for r in results:
            assert 0.0 <= r["score"] <= 1.0, f"Invalid score: {r['score']}"

    def test_no_duplicates(self, retriever):
        """No duplicate chunks in results (same fund_slug + section + chunk_index)."""
        results = retriever.retrieve("compare all HDFC funds returns")
        ids = set()
        for r in results:
            m   = r["metadata"]
            key = (m.get("fund_slug"), m.get("section"), m.get("chunk_index"))
            assert key not in ids, f"Duplicate chunk: {key}"
            ids.add(key)

    def test_fallback_on_restrictive_filter(self, retriever):
        """Retriever returns results even for very specific queries (fallback works)."""
        results = retriever.retrieve("xirr performance benchmark 10 year")
        assert len(results) >= 1, "No results returned even with fallback"

    def test_debug_mode_returns_intent(self, retriever):
        """debug=True returns (chunks, intent) tuple."""
        result = retriever.retrieve("NAV of HDFC Mid Cap", debug=True)
        assert isinstance(result, tuple)
        chunks, intent = result
        assert isinstance(chunks, list)
        assert isinstance(intent, dict)
        assert "section_hints" in intent
        assert "fund_filter" in intent


# ── 3.2: Prompt Builder Tests ─────────────────────────────────────────────────

class TestPromptBuilder:

    def test_build_prompt_returns_tuple(self):
        """build_prompt returns (system_prompt, user_message) tuple."""
        from llm.prompt_builder import build_prompt
        chunks = [
            {
                "content":  "Fund: HDFC Mid Cap Fund\nNAV: Rs.226.92",
                "metadata": {"fund_name": "HDFC Mid Cap Fund Direct Growth", "section": "overview"},
                "score":    0.92,
            }
        ]
        result = build_prompt("What is the NAV?", chunks)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_system_prompt_contains_rules(self):
        """System prompt contains grounding rules."""
        from llm.prompt_builder import build_prompt, SYSTEM_PROMPT
        assert "RESPONSE FORMAT" in SYSTEM_PROMPT or "RULES" in SYSTEM_PROMPT
        assert "HDFC" in SYSTEM_PROMPT
        assert "Do NOT use outside knowledge" in SYSTEM_PROMPT
        assert "investment advice" in SYSTEM_PROMPT.lower() or "financial advice" in SYSTEM_PROMPT.lower()

    def test_user_message_contains_context(self):
        """User message includes the chunk content."""
        from llm.prompt_builder import build_prompt
        chunks = [
            {
                "content":  "NAV: Rs.226.92 | AUM: Rs.97,350 Cr",
                "metadata": {"fund_name": "HDFC Mid Cap Fund Direct Growth", "section": "overview"},
                "score":    0.90,
            }
        ]
        _, user_msg = build_prompt("What is the NAV?", chunks)
        assert "NAV: Rs.226.92" in user_msg
        assert "QUESTION:" in user_msg
        assert "CONTEXT:" in user_msg
        assert "ANSWER:" in user_msg

    def test_user_message_contains_query(self):
        """User message includes the user's query."""
        from llm.prompt_builder import build_prompt
        query = "What is the 5Y return of HDFC Mid Cap?"
        chunks = [
            {
                "content":  "5Y: Annualised +20.87%",
                "metadata": {"fund_name": "HDFC Mid Cap Fund Direct Growth", "section": "returns"},
                "score":    0.88,
            }
        ]
        _, user_msg = build_prompt(query, chunks)
        assert query in user_msg

    def test_multiple_chunks_all_included(self):
        """All retrieved chunks appear in the context."""
        from llm.prompt_builder import build_prompt
        chunks = [
            {"content": "Chunk A content", "metadata": {"fund_name": "Fund A", "section": "overview"}, "score": 0.9},
            {"content": "Chunk B content", "metadata": {"fund_name": "Fund B", "section": "returns"}, "score": 0.8},
        ]
        _, user_msg = build_prompt("test query", chunks)
        assert "Chunk A content" in user_msg
        assert "Chunk B content" in user_msg

    def test_empty_chunks_handled(self):
        """build_prompt handles empty chunk list gracefully."""
        from llm.prompt_builder import build_prompt
        _, user_msg = build_prompt("test query", [])
        assert "No relevant information" in user_msg

    def test_context_summary(self):
        """build_context_summary returns a human-readable one-liner."""
        from llm.prompt_builder import build_context_summary
        chunks = [
            {"content": "x", "metadata": {"fund_name": "HDFC Mid Cap Fund Direct Growth", "section": "overview"}, "score": 0.9},
            {"content": "y", "metadata": {"fund_name": "HDFC Mid Cap Fund Direct Growth", "section": "returns"}, "score": 0.8},
        ]
        summary = build_context_summary(chunks)
        assert isinstance(summary, str)
        assert "2 chunks" in summary
        assert "Mid Cap" in summary


# ── 3.3-3.4: QueryPipeline (requires Groq API key + ChromaDB) ─────────────────

class TestQueryPipeline:
    """
    End-to-end tests that call the Groq API.
    Skipped automatically if GROQ_API_KEY is not set.
    """

    def test_pipeline_runs_nav_query(self, pipeline):
        """Pipeline answers a NAV question without errors."""
        result = pipeline.run("What is the NAV of HDFC Mid Cap Fund?")
        assert "answer" in result
        assert result["answer"].strip(), "Answer should not be empty"
        assert "226" in result["answer"] or "mid cap" in result["answer"].lower()

    def test_pipeline_returns_source_attribution(self, pipeline):
        """Pipeline result includes source fund and section info."""
        result = pipeline.run("What is the expense ratio of HDFC Gold ETF?")
        assert "source_funds" in result
        assert "source_sections" in result
        assert len(result["source_funds"]) >= 1
        assert result["num_chunks"] >= 1

    def test_pipeline_returns_token_count(self, pipeline):
        """Pipeline result includes token usage metadata."""
        result = pipeline.run("What is the minimum SIP for HDFC Silver ETF?")
        assert "input_tokens" in result
        assert "output_tokens" in result
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0

    def test_pipeline_handles_comparative_query(self, pipeline):
        """Pipeline handles comparative queries across funds."""
        result = pipeline.run("Compare the expense ratio of HDFC Mid Cap vs HDFC Large Cap Fund")
        assert result["answer"].strip()
        assert len(result["source_funds"]) >= 1

    def test_pipeline_handles_unknown_query(self, pipeline):
        """Pipeline returns a graceful 'I don't have this info' response for unknown queries."""
        result = pipeline.run("What is the price of bitcoin?")
        answer = result["answer"].lower()
        # Should not hallucinate — should say it doesn't know
        has_disclaimer = any(phrase in answer for phrase in [
            "don't have", "not in my knowledge", "context", "i cannot", "no information",
            "facts-only", "cannot provide", "factual information"
        ])
        assert has_disclaimer, f"Expected disclaimer for out-of-scope query, got: {result['answer'][:100]}"

    def test_pipeline_debug_mode(self, pipeline):
        """debug=True returns retrieved chunks and intent in result."""
        result = pipeline.run("Who manages HDFC Small Cap Fund?", debug=True)
        assert "retrieved_chunks" in result
        assert "intent" in result
        assert isinstance(result["retrieved_chunks"], list)
        assert isinstance(result["intent"], dict)
