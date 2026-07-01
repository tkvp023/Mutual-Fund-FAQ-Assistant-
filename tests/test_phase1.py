"""
Phase 1 Tests — Scraper and Content Extractor

Tests the scraper (using cached HTML, not live scraping) and the
ContentExtractor using the __NEXT_DATA__ strategy.

Run:
    pytest tests/test_phase1.py -v
"""

import os
import sys
import json
import pytest

# Project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mid_cap_html():
    """Load saved Mid Cap fund HTML (avoids live scraping in tests)."""
    path = os.path.join(ROOT, "data", "raw_html", "hdfc-mid-cap-fund-direct-growth.html")
    if not os.path.exists(path):
        pytest.skip(f"Raw HTML not found: {path}. Run scraper first.")
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def mid_cap_doc(mid_cap_html):
    """Extract a full doc dict from Mid Cap HTML."""
    from extractor.content_extractor import ContentExtractor
    extractor = ContentExtractor()
    return extractor.extract(
        mid_cap_html,
        "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    )


@pytest.fixture(scope="module")
def mid_cap_json():
    """Load the saved extracted JSON (faster than re-extracting)."""
    path = os.path.join(ROOT, "data", "extracted", "hdfc-mid-cap-fund-direct-growth.json")
    if not os.path.exists(path):
        pytest.skip("Extracted JSON not found. Run scripts/run_phase2.py first.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── 1.6: Content Extractor Tests ─────────────────────────────────────────────

class TestContentExtractor:

    def test_extractor_returns_dict(self, mid_cap_doc):
        """Extractor output is a dict with expected top-level keys."""
        assert isinstance(mid_cap_doc, dict)
        required_keys = [
            "fund_name", "nav", "aum_cr", "expense_ratio",
            "category", "sub_category", "holdings", "faq",
            "returns_annualised", "sections", "raw_text",
        ]
        for key in required_keys:
            assert key in mid_cap_doc, f"Missing key: {key}"

    def test_fund_name(self, mid_cap_doc):
        """Fund name extracted correctly from __NEXT_DATA__."""
        assert mid_cap_doc["fund_name"] == "HDFC Mid Cap Fund Direct Growth"

    def test_nav_is_float(self, mid_cap_doc):
        """NAV is a float, not a string comma or placeholder."""
        nav = mid_cap_doc["nav"]
        assert isinstance(nav, float), f"NAV should be float, got {type(nav)}: {nav}"
        assert nav > 100, f"NAV {nav} is suspiciously low for Mid Cap"
        # Should NOT be the old broken values
        assert nav != 0
        assert str(nav) != ","

    def test_nav_specific_value(self, mid_cap_json):
        """NAV matches expected value from __NEXT_DATA__."""
        assert mid_cap_json["nav"] == 226.915

    def test_aum_is_float(self, mid_cap_doc):
        """AUM is a float in crores."""
        aum = mid_cap_doc["aum_cr"]
        assert isinstance(aum, float), f"AUM should be float, got {type(aum)}"
        assert aum > 10_000, f"AUM {aum} Cr is too low for a major fund"

    def test_aum_specific_value(self, mid_cap_json):
        """AUM matches expected value."""
        assert abs(mid_cap_json["aum_cr"] - 97350.4842) < 0.01

    def test_expense_ratio(self, mid_cap_doc):
        """Expense ratio is a string like '0.75'."""
        er = mid_cap_doc["expense_ratio"]
        assert er, "Expense ratio should not be empty"
        assert float(er) > 0
        assert float(er) < 5, f"Expense ratio {er}% seems too high"

    def test_expense_ratio_specific(self, mid_cap_json):
        """Expense ratio matches expected value."""
        assert mid_cap_json["expense_ratio"] == "0.75"

    def test_holdings_count(self, mid_cap_doc):
        """Holdings list has correct count and structure."""
        holdings = mid_cap_doc["holdings"]
        assert isinstance(holdings, list)
        assert len(holdings) == 78, f"Expected 78 holdings, got {len(holdings)}"

    def test_holdings_structure(self, mid_cap_doc):
        """Each holding has the required fields."""
        for h in mid_cap_doc["holdings"][:5]:
            assert "name" in h
            assert "sector" in h
            assert "pct" in h
            assert h["name"], "Holding name should not be empty"

    def test_returns_annualised(self, mid_cap_doc):
        """Returns dict has the expected period keys."""
        returns = mid_cap_doc["returns_annualised"]
        assert isinstance(returns, dict)
        expected_periods = ["1m", "3m", "6m", "1y", "3y", "5y", "10y"]
        for period in expected_periods:
            assert period in returns, f"Missing return period: {period}"
        # All values should be floats
        for period, val in returns.items():
            assert isinstance(val, float), f"Return[{period}] should be float, got {type(val)}"

    def test_faq_list(self, mid_cap_doc):
        """FAQ list has 8 items and all answers are plain text (no HTML tags)."""
        faqs = mid_cap_doc["faq"]
        assert isinstance(faqs, list)
        assert len(faqs) == 8, f"Expected 8 FAQs, got {len(faqs)}"
        for qa in faqs:
            assert "question" in qa
            assert "answer" in qa
            assert "<p>" not in qa["answer"], "FAQ answer contains raw HTML <p> tag"
            assert "<ul>" not in qa["answer"], "FAQ answer contains raw HTML <ul> tag"
            assert "<li>" not in qa["answer"], "FAQ answer contains raw HTML <li> tag"
            assert qa["question"], "FAQ question should not be empty"

    def test_category(self, mid_cap_doc):
        """Category and sub_category are correctly extracted."""
        assert mid_cap_doc["category"] == "Equity"
        assert mid_cap_doc["sub_category"] == "Mid Cap"

    def test_isin(self, mid_cap_doc):
        """ISIN code is extracted."""
        isin = mid_cap_doc["isin"]
        assert isin, "ISIN should not be empty"
        assert len(isin) == 12, f"ISIN should be 12 chars, got: {isin}"

    def test_sections_dict(self, mid_cap_doc):
        """Section-split text dict has expected section keys."""
        sections = mid_cap_doc["sections"]
        assert isinstance(sections, dict)
        expected_sections = ["overview", "returns", "holdings", "faq_section"]
        for sec in expected_sections:
            assert sec in sections, f"Missing section: {sec}"

    def test_raw_text_not_empty(self, mid_cap_doc):
        """Raw text is non-empty and substantial."""
        raw = mid_cap_doc["raw_text"]
        assert isinstance(raw, str)
        assert len(raw) > 5000, f"Raw text too short: {len(raw)} chars"

    def test_all_5_funds_extract(self):
        """All 5 HTML files extract without errors."""
        from extractor.content_extractor import ContentExtractor
        extractor = ContentExtractor()
        html_dir = os.path.join(ROOT, "data", "raw_html")
        html_files = [f for f in os.listdir(html_dir) if f.endswith(".html")]

        if not html_files:
            pytest.skip("No HTML files found. Run scraper first.")

        for fname in html_files:
            fpath = os.path.join(html_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                html = f.read()
            slug = fname.replace(".html", "")
            url  = f"https://groww.in/mutual-funds/{slug}"
            doc  = extractor.extract(html, url)

            assert doc["fund_name"], f"{fname}: fund_name is empty"
            assert doc["nav"] is not None, f"{fname}: nav is None"
            assert isinstance(doc["nav"], float), f"{fname}: nav is not float"
            assert len(doc["holdings"]) > 0, f"{fname}: no holdings"
            assert len(doc["faq"]) > 0, f"{fname}: no FAQs"


# ── 1.1: Project Structure Test ───────────────────────────────────────────────

class TestProjectStructure:

    def test_required_directories_exist(self):
        """All required package directories exist."""
        required_dirs = [
            "scraper", "extractor", "chunker", "embeddings",
            "vectorstore", "retriever", "llm", "pipeline",
            "config", "data", "tests",
        ]
        for d in required_dirs:
            path = os.path.join(ROOT, d)
            assert os.path.isdir(path), f"Directory missing: {d}/"

    def test_init_files_exist(self):
        """All packages have __init__.py files."""
        packages = [
            "scraper", "extractor", "chunker", "embeddings",
            "vectorstore", "retriever", "llm", "pipeline", "config",
        ]
        for pkg in packages:
            init_path = os.path.join(ROOT, pkg, "__init__.py")
            assert os.path.exists(init_path), f"Missing: {pkg}/__init__.py"

    def test_env_file_exists(self):
        """.env file exists (Groq API key configured)."""
        env_path = os.path.join(ROOT, ".env")
        assert os.path.exists(env_path), ".env file not found. Copy .env.example and add your GROQ_API_KEY."

    def test_groq_api_key_configured(self):
        """GROQ_API_KEY is set in settings."""
        from config.settings import GROQ_API_KEY
        assert GROQ_API_KEY, (
            "GROQ_API_KEY is empty. Set it in .env:\n  GROQ_API_KEY=gsk_..."
        )

    def test_settings_loadable(self):
        """Settings module loads all required constants."""
        from config.settings import (
            GROQ_API_KEY, GROQ_MODEL, EMBEDDING_MODEL, EMBEDDING_DEVICE,
            CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, TOP_K,
        )
        assert EMBEDDING_MODEL == "BAAI/bge-small-en-v1.5"
        assert TOP_K > 0
