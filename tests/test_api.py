"""
Phase 4 Tests — FastAPI Backend

Tests all API endpoints using FastAPI's TestClient (no live server needed).
The pipeline is loaded once via the lifespan context.

Run:
    pytest tests/test_api.py -v
    pytest tests/test_api.py -v -k "not test_chat"  # skip LLM calls
"""

import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from app.api import app, FUND_CATALOGUE, SUGGESTED_QUESTIONS

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Create a TestClient that also runs the startup lifespan (loads pipeline)."""
    with TestClient(app) as c:
        yield c


# ── /api/health ───────────────────────────────────────────────────────────────

class TestHealth:

    def test_health_returns_200(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_health_status_ok(self, client):
        body = client.get("/api/health").json()
        assert body["status"] == "ok"

    def test_health_pipeline_loaded(self, client):
        body = client.get("/api/health").json()
        assert body["pipeline_loaded"] is True

    def test_health_chunks_in_db(self, client):
        body = client.get("/api/health").json()
        assert body["chunks_in_db"] == 128

    def test_health_has_collection(self, client):
        body = client.get("/api/health").json()
        assert body["collection"] == "hdfc_funds"


# ── /api/funds ────────────────────────────────────────────────────────────────

class TestFunds:

    def test_funds_returns_200(self, client):
        r = client.get("/api/funds")
        assert r.status_code == 200

    def test_funds_total_five(self, client):
        body = client.get("/api/funds").json()
        assert body["total"] == 5
        assert len(body["funds"]) == 5

    def test_funds_contain_all_hdfc_funds(self, client):
        body  = client.get("/api/funds").json()
        names = [f["name"] for f in body["funds"]]
        assert "HDFC Mid Cap Fund Direct Growth"                    in names
        assert "HDFC Large Cap Fund Direct Growth"                  in names
        assert "HDFC Small Cap Fund Direct Growth"                  in names
        assert "HDFC Gold ETF Fund of Fund Direct Plan Growth"      in names
        assert "HDFC Silver ETF FoF Direct Growth"                  in names

    def test_funds_have_required_fields(self, client):
        body = client.get("/api/funds").json()
        required = ["name", "slug", "category", "sub_category", "url", "risk", "color"]
        for fund in body["funds"]:
            for field in required:
                assert field in fund, f"Missing field '{field}' in fund: {fund['name']}"

    def test_funds_slugs_are_valid(self, client):
        body = client.get("/api/funds").json()
        for fund in body["funds"]:
            slug = fund["slug"]
            assert slug, "slug should not be empty"
            assert " " not in slug, f"slug should not contain spaces: {slug}"
            assert slug == slug.lower(), f"slug should be lowercase: {slug}"

    def test_funds_urls_are_groww(self, client):
        body = client.get("/api/funds").json()
        for fund in body["funds"]:
            assert fund["url"].startswith("https://groww.in/mutual-funds/")

    def test_funds_categories(self, client):
        body       = client.get("/api/funds").json()
        categories = {f["category"] for f in body["funds"]}
        assert "Equity"    in categories
        assert "Commodity" in categories

    def test_funds_have_color_codes(self, client):
        body = client.get("/api/funds").json()
        for fund in body["funds"]:
            color = fund["color"]
            assert color.startswith("#"), f"Color should be hex: {color}"
            assert len(color) == 7, f"Color should be 7 chars: {color}"

    def test_funds_have_suggested_questions(self, client):
        body = client.get("/api/funds").json()
        assert "suggested_questions" in body
        assert len(body["suggested_questions"]) >= 5
        for q in body["suggested_questions"]:
            assert isinstance(q, str)
            assert len(q) > 10


# ── /api/chat (POST) ──────────────────────────────────────────────────────────

class TestChat:

    def test_chat_returns_200(self, client):
        r = client.post("/api/chat", json={"query": "What is the NAV of HDFC Mid Cap Fund?"})
        assert r.status_code == 200

    def test_chat_response_has_answer(self, client):
        body = client.post(
            "/api/chat",
            json={"query": "What is the NAV of HDFC Mid Cap Fund?"},
        ).json()
        assert "answer" in body
        assert body["answer"].strip(), "Answer should not be empty"

    def test_chat_response_schema(self, client):
        body = client.post(
            "/api/chat",
            json={"query": "expense ratio of HDFC Gold ETF"},
        ).json()
        required = [
            "answer", "query", "session_id", "source_funds",
            "source_sections", "source_urls", "num_chunks",
            "context_summary", "model", "input_tokens",
            "output_tokens", "response_time_ms",
        ]
        for field in required:
            assert field in body, f"Missing field in response: {field}"

    def test_chat_session_id_auto_generated(self, client):
        """If no session_id provided, one is auto-generated."""
        body = client.post(
            "/api/chat",
            json={"query": "What is the AUM of HDFC Mid Cap Fund?"},
        ).json()
        assert "session_id" in body
        assert body["session_id"], "session_id should not be empty"

    def test_chat_session_id_preserved(self, client):
        """Provided session_id is echoed back in the response."""
        sid  = "test-session-xyz"
        body = client.post(
            "/api/chat",
            json={"query": "returns of HDFC Small Cap Fund", "session_id": sid},
        ).json()
        assert body["session_id"] == sid

    def test_chat_source_funds_populated(self, client):
        body = client.post(
            "/api/chat",
            json={"query": "exit load of HDFC Silver ETF FoF"},
        ).json()
        assert len(body["source_funds"]) >= 1
        assert all(isinstance(f, str) for f in body["source_funds"])

    def test_chat_num_chunks_positive(self, client):
        body = client.post(
            "/api/chat",
            json={"query": "who manages HDFC Mid Cap Fund"},
        ).json()
        assert body["num_chunks"] >= 1

    def test_chat_response_time_ms_positive(self, client):
        body = client.post(
            "/api/chat",
            json={"query": "What is the minimum SIP for HDFC Large Cap Fund?"},
        ).json()
        assert body["response_time_ms"] > 0

    def test_chat_token_counts_positive(self, client):
        body = client.post(
            "/api/chat",
            json={"query": "Sharpe ratio of HDFC Small Cap Fund"},
        ).json()
        assert body["input_tokens"] > 0
        assert body["output_tokens"] > 0

    def test_chat_query_validation_too_short(self, client):
        """Query shorter than 3 chars should return 422."""
        r = client.post("/api/chat", json={"query": "hi"})
        assert r.status_code == 422

    def test_chat_query_validation_too_long(self, client):
        """Query longer than 500 chars should return 422."""
        r = client.post("/api/chat", json={"query": "x" * 501})
        assert r.status_code == 422

    def test_chat_debug_mode_includes_chunks(self, client):
        """debug=True should return retrieved_chunks and intent in response."""
        body = client.post(
            "/api/chat",
            json={"query": "NAV of HDFC Mid Cap Fund", "debug": True},
        ).json()
        assert body["retrieved_chunks"] is not None
        assert body["intent"] is not None
        assert isinstance(body["retrieved_chunks"], list)
        assert len(body["retrieved_chunks"]) >= 1

    def test_chat_debug_false_no_chunks(self, client):
        """debug=False (default) should NOT return retrieved_chunks."""
        body = client.post(
            "/api/chat",
            json={"query": "NAV of HDFC Mid Cap Fund", "debug": False},
        ).json()
        assert body.get("retrieved_chunks") is None

    def test_chat_nav_answer_mentions_fund(self, client):
        """NAV answer should mention the fund name."""
        body = client.post(
            "/api/chat",
            json={"query": "What is the NAV of HDFC Mid Cap Fund?"},
        ).json()
        answer = body["answer"].lower()
        assert "mid cap" in answer or "hdfc" in answer, (
            f"Answer doesn't mention the fund: {body['answer'][:100]}"
        )

    def test_chat_out_of_scope_graceful(self, client):
        """Out-of-scope query should return a graceful 'I don't know' response."""
        body = client.post(
            "/api/chat",
            json={"query": "What is the capital of France?"},
        ).json()
        answer = body["answer"].lower()
        has_disclaimer = any(phrase in answer for phrase in [
            "don't have", "not in my knowledge", "context",
            "i cannot", "no information", "outside",
        ])
        assert has_disclaimer, (
            f"Expected graceful disclaimer, got: {body['answer'][:100]}"
        )


# ── /api/chat/history ─────────────────────────────────────────────────────────

class TestChatHistory:

    def test_history_empty_for_new_session(self, client):
        r = client.get("/api/chat/history/brand-new-session-id")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 0
        assert body["messages"] == []

    def test_history_populated_after_chat(self, client):
        sid = "history-test-session"
        client.post("/api/chat", json={
            "query":      "What is the NAV of HDFC Mid Cap Fund?",
            "session_id": sid,
        })
        history = client.get(f"/api/chat/history/{sid}").json()
        assert history["count"] == 2   # 1 user + 1 assistant
        assert history["messages"][0]["role"] == "user"
        assert history["messages"][1]["role"] == "assistant"
        assert history["messages"][0]["content"] == "What is the NAV of HDFC Mid Cap Fund?"

    def test_history_grows_with_each_message(self, client):
        sid = "multi-turn-session"
        client.post("/api/chat", json={"query": "NAV of HDFC Gold ETF?",    "session_id": sid})
        client.post("/api/chat", json={"query": "And the expense ratio?",    "session_id": sid})
        history = client.get(f"/api/chat/history/{sid}").json()
        assert history["count"] == 4  # 2 questions + 2 answers

    def test_history_clear(self, client):
        sid = "clear-test-session"
        client.post("/api/chat", json={"query": "NAV of HDFC Silver ETF?", "session_id": sid})
        # Verify it has messages
        assert client.get(f"/api/chat/history/{sid}").json()["count"] > 0
        # Clear
        r = client.delete(f"/api/chat/history/{sid}")
        assert r.status_code == 200
        assert r.json()["cleared"] is True
        # Verify empty after clear
        assert client.get(f"/api/chat/history/{sid}").json()["count"] == 0


# ── Root endpoint ─────────────────────────────────────────────────────────────

class TestRoot:

    def test_root_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_root_has_api_links(self, client):
        body = client.get("/").json()
        assert "docs"   in body
        assert "health" in body
        assert "funds"  in body
        assert "chat"   in body
