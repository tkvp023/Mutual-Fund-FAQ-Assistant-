# Phase-wise Implementation Plan

> **Reference:** [Architecture.md](file:///c:/Users/THARUN/Videos/RAG-based%20Mutual%20Fund%20FAQ%20Chatbot/DOCS/Architecture.md) | [problemStatement.md](file:///c:/Users/THARUN/Videos/RAG-based%20Mutual%20Fund%20FAQ%20Chatbot/DOCS/problemStatement.md)
> **LLM Provider:** Groq (LPU-accelerated inference)
> **Embedding Model:** BAAI/bge-small-en-v1.5 (BGE)
> **Last Updated:** June 2026

---

## Implementation Overview

The project is divided into **6 phases**, each building on the previous one. Each phase has a clear deliverable and can be independently tested.

```
Phase 1          Phase 2          Phase 3          Phase 4          Phase 5          Phase 6
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Project  │───▶│ Data     │───▶│ RAG      │───▶│ Chat UI  │───▶│ Polish   │───▶│ Scheduler│
│ Setup &  │    │ Ingestion│    │ Pipeline │    │ & App    │    │ & Test   │    │ (GitHub  │
│ Scraping │    │ Pipeline │    │ (Groq)   │    │ (Stream- │    │          │    │ Actions) │
│          │    │ (BGE)    │    │          │    │  lit)    │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
   ~2 days        ~2 days        ~2 days         ~1.5 days       ~1.5 days       ~1 day
```

**Total Estimated Duration:** ~11–12 days

---

## Phase 1: Project Setup & Web Scraping

> **Goal:** Set up the project structure, install dependencies, and scrape data from the 5 Groww URLs.
> **Duration:** ~2 days

### 1.1 Initialize Project Structure

Create the full directory structure as defined in the architecture.

```
RAG-based Mutual Fund FAQ Chatbot/
├── DOCS/
│   ├── problemStatement.md
│   ├── Architecture.md
│   └── implementation_plan.md
├── config/
│   ├── __init__.py
│   ├── fund_urls.py
│   ├── settings.py
│   └── prompts.py
├── scraper/
│   ├── __init__.py
│   └── groww_scraper.py
├── extractor/
│   ├── __init__.py
│   └── content_extractor.py
├── chunker/
│   ├── __init__.py
│   └── text_chunker.py
├── embeddings/
│   ├── __init__.py
│   └── embedder.py
├── vectorstore/
│   ├── __init__.py
│   └── store.py
├── retriever/
│   ├── __init__.py
│   └── retriever.py
├── llm/
│   ├── __init__.py
│   ├── prompt_builder.py
│   └── generator.py
├── app/
│   └── chatbot.py
├── pipeline/
│   ├── __init__.py
│   ├── ingest.py
│   └── query.py
├── tests/
│   ├── test_scraper.py
│   ├── test_extractor.py
│   ├── test_chunker.py
│   ├── test_retriever.py
│   └── test_e2e.py
├── chroma_db/                  # Auto-created by ChromaDB
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
└── README.md
```

### 1.2 Install Dependencies

**`requirements.txt`:**

```
# Core
langchain>=0.2.0
langchain-community>=0.2.0
chromadb>=0.4.0

# Embeddings (BGE model)
sentence-transformers>=2.2.0

# Web Scraping
selenium>=4.15.0
beautifulsoup4>=4.12.0
webdriver-manager>=4.0.0

# LLM Provider (Groq)
langchain-groq>=0.1.0
groq>=0.5.0

# Frontend
streamlit>=1.30.0

# Utilities
python-dotenv>=1.0.0
requests>=2.31.0

# Testing
pytest>=8.0.0
```

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows

# Install all dependencies
pip install -r requirements.txt
```

### 1.3 Configure Environment

**`.env`:**

```env
GROQ_API_KEY=your_groq_api_key_here

# Model Config
GROQ_MODEL=llama-3.1-8b-instant
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Pipeline Settings
CHUNK_SIZE=800
CHUNK_OVERLAP=150
TOP_K=5
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=800
```

**`.gitignore`:**

```
venv/
chroma_db/
.env
__pycache__/
*.pyc
.pytest_cache/
```

### 1.4 Create URL Config

**`config/fund_urls.py`:**

```python
FUND_URLS = [
    "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
]
```

### 1.5 Build Web Scraper

**`scraper/groww_scraper.py`:**

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

class GrowwScraper:
    def __init__(self, urls: list[str], wait_time: int = 5):
        self.urls = urls
        self.wait_time = wait_time

    def _get_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def scrape(self, url: str) -> str:
        driver = self._get_driver()
        try:
            driver.get(url)
            time.sleep(self.wait_time)  # Wait for JS rendering
            return driver.page_source
        finally:
            driver.quit()

    def scrape_all(self) -> dict[str, str]:
        results = {}
        for url in self.urls:
            print(f"Scraping: {url}")
            results[url] = self.scrape(url)
            time.sleep(2)  # Rate limiting
        return results
```

### 1.6 Build Content Extractor

**Primary source: `__NEXT_DATA__` JSON** — Groww is a Next.js app that embeds the full API response in a `<script id="__NEXT_DATA__">` tag. This contains all structured fund data (NAV, AUM, returns, holdings, managers, peers) in a single clean JSON object, making regex-on-text approaches unnecessary and unreliable.

**`extractor/content_extractor.py`:**

```python
from bs4 import BeautifulSoup
from datetime import datetime
import json, re

class ContentExtractor:
    """
    Primary extraction: __NEXT_DATA__ JSON (Next.js SSR payload)
    Secondary:          JSON-LD FAQPage schema (clean Q&A pairs)
    Tertiary:           Section-split raw text (for section-aware chunker)
    """

    def extract(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        mf   = self._extract_next_data(soup)      # all structured data
        faq  = self._extract_faq_jsonld(soup)     # clean Q&A from JSON-LD
        raw_text = self._extract_clean_text(soup) # de-noised visible text
        sections = self._split_into_sections(raw_text)  # named sections dict

        return {
            # identity
            "fund_name":   mf.get("scheme_name"),
            "fund_slug":   url.rstrip("/").split("/")[-1],
            "source_url":  url,
            "scraped_at":  datetime.now().isoformat(),
            "isin":        mf.get("isin", ""),

            # key metrics — all from __NEXT_DATA__, not regex
            "nav":             mf.get("nav"),          # float e.g. 226.915
            "nav_date":        mf.get("nav_date", ""),
            "aum_cr":          mf.get("aum"),          # float crores
            "expense_ratio":   mf.get("expense_ratio", ""),
            "category":        mf.get("category", ""),
            "sub_category":    mf.get("sub_category", ""),
            "benchmark":       mf.get("benchmark_name", ""),
            "groww_rating":    mf.get("groww_rating"),
            "launch_date":     mf.get("launch_date", ""),
            "min_lumpsum":     mf.get("min_investment_amount"),
            "min_sip":         mf.get("min_sip_investment"),
            "exit_load":       mf.get("exit_load", ""),
            "stamp_duty":      mf.get("stamp_duty", ""),
            "lock_in":         self._parse_lock_in(mf.get("lock_in", {})),
            "description":     mf.get("description", ""),

            # returns (annualised % and SIP XIRR) — 10 periods
            "returns_annualised": self._parse_returns(mf.get("return_stats")),
            "returns_sip":        self._parse_returns(mf.get("sip_return")),

            # risk / ranking stats
            "stats":     self._parse_stats(mf.get("return_stats")),

            # structured holdings [{name, sector, instrument, pct}, ...]
            "holdings":  self._parse_holdings(mf.get("holdings", [])),

            # fund managers [{name, since, education, experience}, ...]
            "fund_managers": self._parse_managers(mf.get("fund_manager_details", [])),

            # peer comparison [{name, return_1y, return_3y, aum_cr}, ...]
            "peers":     self._parse_peers(mf.get("peerComparison", [])),

            # pros/cons analysis
            "analysis":  self._parse_analysis(mf.get("analysis", [])),

            # FAQ — from JSON-LD (HTML tags stripped from answers)
            "faq":       faq,

            # AMC info
            "amc_info":  self._parse_amc(mf.get("amc_info", {})),

            # section-split raw text dict (for SectionAwareChunker)
            "sections":  sections,

            # flat raw text (fallback)
            "raw_text":       raw_text,
            "raw_text_length": len(raw_text),
        }

    def _extract_next_data(self, soup) -> dict:
        """Read props.pageProps.mfServerSideData from __NEXT_DATA__ JSON."""
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return {}
        data = json.loads(script.string)
        return data["props"]["pageProps"]["mfServerSideData"]

    def _extract_faq_jsonld(self, soup) -> list:
        """Extract FAQ Q&A from FAQPage JSON-LD schema; strip HTML from answers."""
        faqs = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue
            if data.get("@type") == "FAQPage":
                for item in data.get("mainEntity", []):
                    q = item.get("name", "").strip()
                    a_raw = (item.get("acceptedAnswer") or {}).get("text", "")
                    a = re.sub(r"\s+", " ",
                               BeautifulSoup(a_raw, "html.parser")
                               .get_text(separator=" ", strip=True))
                    if q:
                        faqs.append({"question": q, "answer": a})
        return faqs
```

> **Why `__NEXT_DATA__`?**
> Groww is a Next.js SSR app. Every page embeds `props.pageProps.mfServerSideData` — the full API payload — inside `<script id="__NEXT_DATA__">`. This gives us:
> - NAV, AUM, expense ratio as proper floats (not parsed strings)
> - All return periods (1d/1w/1m/3m/6m/1y/3y/5y/10y/since-inception) with correct values
> - 78+ structured holdings rows with name, sector, instrument type, corpus %
> - Fund manager details (education, experience, tenure)
> - Category rankings and category-average returns
> - Peer comparison table
> - No regex, no brittle CSS-class selectors needed

### Phase 1 Deliverables

| # | Deliverable | Verification |
|---|-------------|-------------|
| 1 | Project directory created | All folders & `__init__.py` files exist |
| 2 | Dependencies installed | `pip list` shows all packages |
| 3 | `.env` configured | Groq API key set and loadable |
| 4 | Scraper works | `scrape_all()` returns HTML for 5 URLs |
| 5 | Extractor works | Text content extracted from each HTML |

### Phase 1 Test

```python
# tests/test_scraper.py
def test_scrape_single_url():
    from scraper.groww_scraper import GrowwScraper
    scraper = GrowwScraper(["https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"])
    result = scraper.scrape_all()
    assert len(result) == 1
    assert "HDFC Mid Cap" in list(result.values())[0]
```

---

## Phase 2: Data Ingestion Pipeline (Chunking + BGE Embeddings + ChromaDB)

> **Goal:** Chunk the extracted text, generate BGE embeddings, and store them in ChromaDB.
> **Duration:** ~2 days

### 2.1 Build Section-Aware Text Chunker

**Design principle:** Each section type from the Groww page gets a dedicated synthesis strategy. The chunker works entirely from the structured `doc` dict produced by `ContentExtractor` — it does **not** do recursive character splitting on raw text.

#### Section → Strategy Map

| Section | Strategy | Output per fund |
|---|---|---|
| `overview` | **Synthesize** — dense fund-card string | 1 chunk |
| `about_fund` | **Synthesize** — narrative + pros/cons | 1 chunk |
| `returns` | **Synthesize** — 10-period table + category avg + ranks | 1 chunk |
| `exit_load_tax` | **Synthesize** — exit load + stamp duty + LTCG/STCG tax | 1 chunk |
| `investment_info` | **Keep whole** — min SIP/lumpsum | 1 chunk |
| `performance_ranking` | **Synthesize** — fund vs category, Sharpe, alpha, beta | 1 chunk |
| `peer_comparison` | **Synthesize** — formatted comparison table | 1 chunk |
| `holdings` | **Group by sector, batch of 10** | ~8–10 chunks |
| `fund_management` | **Per-manager** — bio only (trim other-funds list) | 1–2 chunks |
| `fund_house` | **Keep whole** | 1 chunk |
| `faq` | **Per Q&A pair** | 8 chunks |

**Every chunk is prefixed** with `[Fund Name | section]` context so the retriever can disambiguate across 5 funds.

#### Chunk Metadata Schema

```python
{
    "fund_name":  "HDFC Mid Cap Fund Direct Growth",
    "fund_slug":  "hdfc-mid-cap-fund-direct-growth",
    "source_url": "https://groww.in/mutual-funds/...",
    "section":    "holdings",          # section type
    "chunk_type": "holdings_batch",    # fine-grained type
    "chunk_index": 3,                  # position within fund
    "scraped_at": "2026-06-28T...",
    # optional: holdings_sector, manager_name, ...
}
```

**`chunker/preprocessor.py`** — synthesizer functions:

```python
def build_overview_chunk(doc: dict) -> str:
    """Dense fund-card with all key metrics."""
    return (
        f"Fund: {doc['fund_name']}\n"
        f"Category: {doc['category']} > {doc['sub_category']}\n"
        f"NAV: ₹{doc['nav']} (as of {doc['nav_date']})\n"
        f"AUM: ₹{doc['aum_cr']:,.2f} Cr\n"
        f"Expense Ratio: {doc['expense_ratio']}%\n"
        f"Risk: {doc['stats'].get('risk')} (Rating: {doc['groww_rating']}/5)\n"
        f"Min SIP: ₹{doc['min_sip']} | Min Lumpsum: ₹{doc['min_lumpsum']}\n"
        f"Exit Load: {doc['exit_load']}\n"
        f"Benchmark: {doc['benchmark']}\n"
        f"Launch Date: {doc['launch_date']}\n"
        f"ISIN: {doc['isin']}"
    )

def build_returns_chunk(doc: dict) -> str:
    """10-period returns table + category comparison + ranks."""
    # Renders: 1M/3M/6M/1Y/3Y/5Y/10Y/Since Inception
    # annualised % and SIP XIRR side-by-side
    # + category avg 1Y/3Y/5Y
    # + category rank 1Y/3Y/5Y/10Y
    ...

def build_holdings_chunks(doc: dict, batch_size: int = 10) -> list:
    """Group by sector, batch within sector."""
    # e.g. "Portfolio Holdings — Financial Sector
    #       Max Financial Services Ltd (Equity) — 4.49%
    #       AU Small Finance Bank Ltd (Equity) — 4.01% ..."
    by_sector = group_by_sector(doc["holdings"])
    for sector, items in by_sector.items():
        for batch in batched(items, batch_size):
            yield format_batch(doc["fund_name"], sector, batch)

def build_faq_chunks(doc: dict) -> list:
    """One chunk per Q&A pair, answers HTML-stripped."""
    for qa in doc["faq"]:
        yield f"Q: {qa['question']}\nA: {qa['answer']}"
```

**`chunker/text_chunker.py`** — `SectionAwareChunker`:

```python
from chunker.preprocessor import (
    build_overview_chunk, build_about_chunk, build_returns_chunk,
    build_exit_load_tax_chunk, build_investment_info_chunk,
    build_holdings_chunks, build_fund_management_chunks,
    build_performance_ranking_chunk, build_peer_comparison_chunk,
    build_fund_house_chunk, build_faq_chunks,
)

class SectionAwareChunker:
    def chunk(self, doc: dict) -> list[dict]:
        """Produce all chunks for a single fund document dict."""
        base_meta = {
            "fund_name":  doc["fund_name"],
            "fund_slug":  doc["fund_slug"],
            "source_url": doc["source_url"],
            "scraped_at": doc["scraped_at"],
        }
        raw_chunks = []  # (section, chunk_type, text, extra_meta)

        # Synthesised single-chunk sections
        for sec, ctype, builder in [
            ("overview",           "overview_card",       build_overview_chunk),
            ("about_fund",         "about",                build_about_chunk),
            ("returns",            "returns_table",        build_returns_chunk),
            ("exit_load_tax",      "exit_load_tax",        build_exit_load_tax_chunk),
            ("investment_info",    "investment_info",      build_investment_info_chunk),
            ("performance_ranking","performance_ranking",  build_performance_ranking_chunk),
            ("peer_comparison",    "peer_comparison",      build_peer_comparison_chunk),
            ("fund_house",         "fund_house",           build_fund_house_chunk),
        ]:
            text = builder(doc)
            if text.strip():
                raw_chunks.append((sec, ctype, text, {}))

        # Multi-chunk sections
        for text, extra in build_holdings_chunks(doc, batch_size=10):
            raw_chunks.append(("holdings", "holdings_batch", text, extra))

        for text, extra in build_fund_management_chunks(doc):
            raw_chunks.append(("fund_management", "fund_manager", text, extra))

        for text, extra in build_faq_chunks(doc):
            raw_chunks.append(("faq", "faq", text, extra))

        # Assemble final chunk dicts with index
        return [
            {"content": content,
             "metadata": {**base_meta, "section": sec, "chunk_type": ctype,
                          "chunk_index": i, **extra}}
            for i, (sec, ctype, content, extra) in enumerate(raw_chunks)
        ]

    def chunk_all(self, documents: list) -> list:
        """Chunk all fund documents, return flat list."""
        all_chunks = []
        for doc in documents:
            chunks = self.chunk(doc)
            all_chunks.extend(chunks)
        return all_chunks
```

#### Actual Chunk Counts (verified on 5 live fund pages)

| Section | Chunks (total, 5 funds) |
|---|---|
| `holdings` (sector-batched, 10/batch) | 40 |
| `faq` (1 per Q&A) | 40 |
| `fund_management` (per manager) | 10 |
| `overview` | 5 |
| `about_fund` | 5 |
| `returns` | 5 |
| `exit_load_tax` | 5 |
| `investment_info` | 5 |
| `performance_ranking` | 5 |
| `fund_house` | 5 |
| `peer_comparison` | 3 |
| **Total** | **128** |

### 2.2 Embedding Strategy

#### Data-Driven Model Selection

Before choosing a model, we analyse the actual chunk characteristics:

**Chunk size distribution (128 chunks across 5 funds):**

| Section | Count | Avg chars | Max chars | Content Nature |
|---|---|---|---|---|
| `holdings` | 40 | 350 | 575 | Tabular: name \| sector \| % |
| `faq` | 40 | 312 | 714 | Short Q&A pairs |
| `exit_load_tax` | 5 | 699 | 828 | Mixed: rules + numbers |
| `returns` | 5 | 569 | 607 | Numeric table (10 periods) |
| `peer_comparison` | 3 | 666 | 667 | Comparison table |
| `overview` | 5 | 401 | 405 | Key-value card |
| `performance_ranking` | 5 | 320 | 345 | Numeric + text |
| `fund_management` | 10 | 302 | 402 | Short narrative |
| `about_fund` | 5 | 349 | 449 | Short narrative |
| `investment_info` | 5 | 166 | 178 | Key-value |
| `fund_house` | 5 | 90 | 90 | Very short key-value |
| **Average (all)** | **128** | **347** | **828** | — |

**Key observations:**
- Average chunk is **347 chars (~85 tokens)** — short, dense, factual
- Largest chunk is **828 chars (~210 tokens)** — well within any model's limit
- Heavy domain vocabulary: NAV, AUM, XIRR, SIP, LTCG, STCG, ETF, FoF, Sharpe, Alpha, Beta (all appear 5–60x)
- **Critical disambiguation challenge**: all 5 funds share prefix `"HDFC ... Direct Growth"`, differing only in `Mid Cap` / `Large Cap` / `Small Cap` / `Gold ETF` / `Silver ETF FoF`
- Queries are short (40–80 chars) and factual — asymmetric query↔document lengths

---

#### BGE-small vs BGE-large: Decision

| Factor | BGE-small-en-v1.5 | BGE-large-en-v1.5 |
|---|---|---|
| **Dimensions** | 384 | 1024 |
| **Model size** | ~33 MB | ~335 MB |
| **MTEB Avg score** | 62.17 | 64.23 |
| **Semantic precision** | Good | Excellent |
| **Short-text retrieval** | ✅ Excellent | ✅ Excellent |
| **Domain-term handling** | ✅ Good (financial terms) | ✅ Better |
| **Sub-category disambiguation** | ⚠️ Adequate | ✅ Better |
| **CPU embed time (128 chunks)** | ~3–5s | ~25–40s |
| **ChromaDB storage (128 chunks)** | ~196 KB | ~524 KB |
| **RAM usage** | ~150 MB | ~1.3 GB |
| **Re-embedding on scrape refresh** | Trivial | Moderate |

> [!NOTE]
> **Verdict: Use `BAAI/bge-small-en-v1.5`** for this project.
>
> **Reasons specific to our data:**
> 1. **Corpus is tiny** — 128 chunks, ~44K total chars. BGE-large's superior precision doesn't materialise until corpora exceed ~10K chunks.
> 2. **Chunks are short and dense** (avg 347 chars). BGE-small handles short texts just as well as BGE-large — the gap in MTEB score comes from long-document tasks.
> 3. **Metadata filtering compensates** — our chunker tags every chunk with `fund_name`, `section`, `chunk_type`. The retriever can apply a metadata pre-filter on `fund_name` before vector search, reducing the disambiguation burden on the embedding model.
> 4. **CPU-only deployment** — BGE-large takes 8–10× longer per embed pass on CPU. Since we will need to re-embed on each scrape refresh, this matters.
> 5. **The score difference is 2 points (62 vs 64)** — negligible when retrieval is already constrained by `top_k=5` over 128 chunks.
>
> **When to upgrade to BGE-large:** If the corpus expands to 10+ funds, if hallucination rates are high in evaluation, or if a GPU is available.

---

#### Implementation

**`embeddings/embedder.py`:**

```python
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
import os

# ── Model config ─────────────────────────────────────────────────────────
# BGE-small: 384-dim, ~33MB, ~3-5s for 128 chunks on CPU
# BGE-large: 1024-dim, ~335MB — upgrade path if corpus grows beyond 1000 chunks
RECOMMENDED_MODEL = "BAAI/bge-small-en-v1.5"

# BGE-small requires an instruction prefix for queries (not for documents).
# LangChain's HuggingFaceBgeEmbeddings handles this automatically.
# For asymmetric retrieval (short query → longer doc), this prefix is critical.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

class BGEEmbedder:
    """
    BGE embedding wrapper.

    Uses BAAI/bge-small-en-v1.5 (384-dim):
      - Chosen over bge-large because corpus is tiny (128 chunks),
        chunks are short (avg 347 chars), and CPU-only deployment
        makes the 8-10x speed difference significant.
      - normalize_embeddings=True enables cosine similarity via dot product.
      - HuggingFaceBgeEmbeddings automatically prepends the query instruction
        prefix for embed_query() calls (not for embed_documents()).
    """

    def __init__(self, model_name: str = RECOMMENDED_MODEL, device: str = "cpu"):
        self.model_name = model_name
        self.model = HuggingFaceBgeEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},  # cosine sim via dot product
        )

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Embed a list of document chunks in batches.

        Args:
            texts:      List of chunk content strings.
            batch_size: Process this many chunks at once (controls RAM).

        Returns:
            List of 384-dim float vectors, one per input text.
        """
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            embeddings = self.model.embed_documents(batch)
            all_embeddings.extend(embeddings)
            print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks...")
        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a single user query (instruction prefix applied automatically).

        Args:
            query: The user's natural language question.

        Returns:
            384-dim float vector.
        """
        return self.model.embed_query(query)

    @property
    def dimensions(self) -> int:
        """Return embedding dimensions (384 for small, 1024 for large)."""
        return 384 if "small" in self.model_name else 1024
```

#### Embedding Behaviour by Chunk Type

| Chunk type | Embedding challenge | Why BGE-small handles it |
|---|---|---|
| `overview` (key-value card) | Short, factual, fund-specific | Short-text retrieval is BGE-small's strength |
| `returns` (numeric table) | Numbers + % signs + period labels | Treats as token sequence; context from fund name prefix |
| `holdings` (name \| sector \| %) | Tabular, entity-dense | Entity names are tokenised correctly |
| `faq` (Q&A pairs) | Asymmetric: query ≈ question, doc = full Q+A | Query instruction prefix bridges the gap |
| `peer_comparison` (table) | Needs to understand fund name relationships | Fund names appear verbatim in chunk |
| `performance_ranking` (stats) | Greek letters (alpha, beta, sharpe) | Standard financial vocabulary |

#### Expected Performance

```
Model:          BAAI/bge-small-en-v1.5
Dimensions:     384
Corpus size:    128 chunks, ~44K chars
Embed time:     ~3-5s (CPU, batch_size=32)
Storage:        128 × 384 × 4 bytes ≈ 196 KB in ChromaDB
Query latency:  <100ms per query on CPU
```



### 2.3 Build Vector Store (ChromaDB)

**`vectorstore/store.py`:**

```python
import chromadb
from embeddings.embedder import BGEEmbedder

class VectorStore:
    def __init__(self, collection_name: str = "hdfc_funds", persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, chunks: list[dict], embeddings: list[list[float]]):
        self.collection.add(
            ids=[f"chunk_{i}" for i in range(len(chunks))],
            documents=[c["content"] for c in chunks],
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in chunks],
        )

    def query(self, query_embedding: list[float], n_results: int = 5) -> dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

    def reset(self):
        """Delete and recreate collection for re-ingestion."""
        self.client.delete_collection("hdfc_funds")
        self.collection = self.client.get_or_create_collection(
            name="hdfc_funds",
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()
```

### 2.4 Build Ingestion Pipeline Orchestrator

**`pipeline/ingest.py`:**

```python
from config.fund_urls import FUND_URLS
from scraper.groww_scraper import GrowwScraper
from extractor.content_extractor import ContentExtractor
from chunker.text_chunker import FundTextChunker
from embeddings.embedder import BGEEmbedder
from vectorstore.store import VectorStore

def run_ingestion():
    print("=" * 60)
    print("INGESTION PIPELINE — Starting")
    print("=" * 60)

    # Step 1: Scrape
    print("\n[1/4] Scraping Groww fund pages...")
    scraper = GrowwScraper(FUND_URLS)
    raw_html = scraper.scrape_all()
    print(f"  ✓ Scraped {len(raw_html)} pages")

    # Step 2: Extract
    print("\n[2/4] Extracting content...")
    extractor = ContentExtractor()
    documents = []
    for url, html in raw_html.items():
        doc = extractor.extract(html, url)
        documents.append(doc)
        print(f"  ✓ {doc['fund_name']} — {len(doc['raw_text'])} chars")

    # Step 3: Chunk
    print("\n[3/4] Chunking text...")
    chunker = FundTextChunker(chunk_size=800, chunk_overlap=150)
    all_chunks = []
    for doc in documents:
        metadata = {
            "fund_name": doc["fund_name"],
            "source_url": doc["source_url"],
            "scraped_at": doc["scraped_at"],
        }
        chunks = chunker.chunk(doc["raw_text"], metadata)
        all_chunks.extend(chunks)
    print(f"  ✓ Generated {len(all_chunks)} chunks")

    # Step 4: Embed + Store
    print("\n[4/4] Generating BGE embeddings & storing in ChromaDB...")
    embedder = BGEEmbedder(model_name="BAAI/bge-small-en-v1.5")
    texts = [c["content"] for c in all_chunks]
    embeddings = embedder.embed_documents(texts)

    store = VectorStore()
    store.reset()
    store.add_documents(all_chunks, embeddings)
    print(f"  ✓ Stored {store.count()} chunks in ChromaDB")

    print("\n" + "=" * 60)
    print("INGESTION PIPELINE — Complete ✓")
    print("=" * 60)

if __name__ == "__main__":
    run_ingestion()
```

### Phase 1 & 2 Deliverables

| # | Deliverable | Verification |
|---|-------------|-------------|
| 1 | `ContentExtractor` reads `__NEXT_DATA__` | `doc['nav']` returns float (e.g. `226.915`), not `','` |
| 2 | All 5 funds extract correctly | `doc['aum_cr']`, `doc['expense_ratio']`, `doc['holdings']` populated |
| 3 | 10 return periods extracted | `doc['returns_annualised']` has keys `1d`…`since_inception` |
| 4 | FAQ answers are plain text | No `<p>/<ul>/<li>` tags in `doc['faq'][*]['answer']` |
| 5 | `SectionAwareChunker` produces 128 chunks | `python scripts/run_phase2.py` prints `Total chunks: 128` |
| 6 | Holdings chunks are sector-grouped | Each holdings chunk header contains sector name |
| 7 | BGE embedder generates vectors | Output shape: `(128, 384)` |
| 8 | ChromaDB stores all chunks | `store.count()` returns `128` |

### Phase 2 Runner

```bash
# Re-extract from existing HTML + chunk (no re-scraping needed)
python scripts/run_phase2.py

# Output:
#   data/extracted/          ← fixed structured JSON (NAV, AUM, returns, holdings)
#   data/extracted/sections/ ← per-fund section-split text
#   data/chunks/             ← all_chunks.json + chunks_readable.txt
#   data/phase2_report.json  ← run report
```

### Phase 2 Tests

```python
# tests/test_extractor.py
def test_next_data_extraction():
    from extractor.content_extractor import ContentExtractor
    import json
    with open("data/extracted/hdfc-mid-cap-fund-direct-growth.json") as f:
        doc = json.load(f)
    assert doc["nav"] == 226.915            # correct float, not ','
    assert doc["aum_cr"] == 97350.4842
    assert doc["expense_ratio"] == "0.75"
    assert len(doc["holdings"]) == 78
    assert len(doc["faq"]) == 8
    # FAQ answers must be plain text
    assert "<p>" not in doc["faq"][0]["answer"]

# tests/test_chunker.py
def test_section_aware_chunker():
    from chunker.text_chunker import SectionAwareChunker
    import json
    # Load a pre-extracted document
    with open("data/chunks/hdfc-mid-cap-fund-direct-growth_chunks.json") as f:
        chunks = json.load(f)
    assert len(chunks) == 31
    sections = [c["metadata"]["section"] for c in chunks]
    assert "overview" in sections
    assert "returns" in sections
    assert "holdings" in sections
    assert "faq" in sections
    # Overview chunk must contain key facts
    overview = next(c for c in chunks if c["metadata"]["section"] == "overview")
    assert "NAV" in overview["content"]
    assert "AUM" in overview["content"]
    assert "Expense Ratio" in overview["content"]

# tests/test_embedder.py
def test_bge_embedding():
    from embeddings.embedder import BGEEmbedder
    embedder = BGEEmbedder()
    vectors = embedder.embed_documents(["HDFC Mid Cap Fund NAV is ₹226.92"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 384  # BGE-small dimension
```

---

## Phase 3: RAG Query Pipeline (Retriever + Groq LLM)

> **Goal:** Build the retrieval chain and connect it to Groq for answer generation.
> **Duration:** ~2 days

### 3.1 Retrieval Strategy

#### Data-Driven Retrieval Analysis

Based on analysis of the actual 128 chunks and the 11 section types, we identified the following retrieval challenges and their solutions:

**Key challenges discovered:**
1. **Fund disambiguation** — All 5 fund names share prefix `"HDFC ... Direct Growth"`. Pure vector search on a generic query like *"What is the expense ratio?"* returns chunks from all 5 funds.
2. **Section specificity** — Different queries map to entirely different sections. A NAV query must hit `overview`, not `holdings` or `faq`.
3. **Cross-fund comparison queries** — Queries like *"Compare 5Y returns of Mid Cap vs Small Cap"* need `returns` chunks from *multiple* funds (top_k=5 with section filter).
4. **Chunk richness imbalance** — `overview` (6/6 facts), `returns` (5/5 facts), `exit_load_tax` (2/4 facts, LTCG missing). Over-relying on single-chunk retrieval misses complementary data.

**Query → Section mapping (from chunk analysis):**

| Query Pattern | Keywords | Target Section(s) | Min k |
|---|---|---|---|
| NAV / AUM / expense / SIP / benchmark | factual metrics | `overview` | 1 |
| Returns / CAGR / XIRR / performance | return periods | `returns`, `performance_ranking` | 1–2 |
| Exit load / tax / LTCG / STCG / redeem | tax/fees | `exit_load_tax` | 1 |
| Holdings / portfolio / sector / stock | portfolio | `holdings` | 1–2 |
| Fund manager / who manages | manager | `fund_management` | 1 |
| Compare / vs / which is better | cross-fund | `peer_comparison`, `returns` | 2–5 |
| How to invest / KYC / steps | procedure | `faq` | 1 |
| Is it good / should I invest / risk | qualitative | `about_fund`, `faq` | 2 |
| Sharpe / alpha / beta / volatility | risk stats | `performance_ranking` | 1 |
| Minimum SIP / minimum investment | minimums | `investment_info`, `overview` | 1 |

**Available metadata fields for filtering:**
```
fund_name, fund_slug, section, chunk_type, chunk_index,
scraped_at, source_url, holdings_sector, manager_name
```

---

#### Retrieval Architecture: Two-Stage with Intent Detection

```
User Query
    │
    ▼
┌─────────────────────────────┐
│  Stage 1: Intent Detection  │  ← keyword-based classifier
│  • Extract fund name(s)     │    (no LLM call, fast)
│  • Classify query type      │
│  • Determine target sections│
└─────────────┬───────────────┘
              │  (fund_filter, section_filter, top_k)
              ▼
┌─────────────────────────────┐
│  Stage 2: Filtered Vector   │  ← BGE embed query → ChromaDB
│  Search                     │    with where= metadata filter
│  • Scoped by fund if named  │
│  • Scoped by section type   │
└─────────────┬───────────────┘
              │  top_k chunks
              ▼
┌─────────────────────────────┐
│  Stage 3: Post-Rank + Dedupe│  ← remove duplicate fund_house
│                             │    chunks, sort by distance
└─────────────────────────────┘
```

---

#### Implementation

**`retriever/intent_detector.py`** — keyword-based query classifier:

```python
import re

# All 5 fund names and their shorthand aliases
FUND_ALIASES = {
    "mid cap":    "HDFC Mid Cap Fund Direct Growth",
    "midcap":     "HDFC Mid Cap Fund Direct Growth",
    "mid-cap":    "HDFC Mid Cap Fund Direct Growth",
    "large cap":  "HDFC Large Cap Fund Direct Growth",
    "largecap":   "HDFC Large Cap Fund Direct Growth",
    "small cap":  "HDFC Small Cap Fund Direct Growth",
    "smallcap":   "HDFC Small Cap Fund Direct Growth",
    "gold etf":   "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "gold":       "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "silver etf": "HDFC Silver ETF FoF Direct Growth",
    "silver":     "HDFC Silver ETF FoF Direct Growth",
}

# Section routing rules: keyword → target sections list
SECTION_ROUTING = {
    # Metric queries → overview (has NAV, AUM, expense, SIP, benchmark, risk in one chunk)
    "nav":           ["overview"],
    "aum":           ["overview"],
    "expense ratio": ["overview", "investment_info"],
    "expense":       ["overview"],
    "benchmark":     ["overview"],
    "minimum sip":   ["investment_info", "overview"],
    "min sip":       ["investment_info", "overview"],
    "minimum investment": ["investment_info", "overview"],
    "isin":          ["overview"],

    # Returns queries
    "return":        ["returns", "performance_ranking"],
    "returns":       ["returns", "performance_ranking"],
    "cagr":          ["returns"],
    "xirr":          ["returns"],
    "performance":   ["returns", "performance_ranking"],
    "1 year":        ["returns"],
    "3 year":        ["returns"],
    "5 year":        ["returns"],

    # Risk/stats
    "sharpe":        ["performance_ranking"],
    "alpha":         ["performance_ranking"],
    "beta":          ["performance_ranking"],
    "volatility":    ["performance_ranking"],
    "standard deviation": ["performance_ranking"],
    "rank":          ["performance_ranking", "returns"],

    # Tax/fees
    "exit load":     ["exit_load_tax"],
    "ltcg":          ["exit_load_tax"],
    "stcg":          ["exit_load_tax"],
    "tax":           ["exit_load_tax"],
    "stamp duty":    ["exit_load_tax"],
    "redeem":        ["exit_load_tax"],

    # Holdings
    "holding":       ["holdings"],
    "holdings":      ["holdings"],
    "portfolio":     ["holdings"],
    "sector":        ["holdings"],
    "stock":         ["holdings"],
    "invest in":     ["holdings"],

    # Fund manager
    "manager":       ["fund_management"],
    "who manages":   ["fund_management"],
    "fund manager":  ["fund_management"],

    # Comparison
    "compare":       ["peer_comparison", "returns"],
    "vs":            ["peer_comparison", "returns"],
    "versus":        ["peer_comparison", "returns"],
    "better":        ["peer_comparison", "returns", "about_fund"],

    # FAQ/procedural
    "how to invest": ["faq"],
    "kyc":           ["faq"],
    "steps":         ["faq"],
    "how to":        ["faq"],

    # Qualitative
    "good":          ["about_fund", "faq"],
    "should i":      ["about_fund", "faq"],
    "recommend":     ["about_fund", "faq"],
    "risk":          ["about_fund", "performance_ranking", "overview"],
}

class IntentDetector:
    """
    Lightweight keyword-based intent detector.

    Returns:
        fund_filter:    exact fund_name string or None (if cross-fund query)
        section_hints:  ordered list of target sections
        is_comparative: True if query spans multiple funds
        top_k:          recommended number of chunks to retrieve
    """

    def detect(self, query: str) -> dict:
        q = query.lower()

        # ── Fund detection ────────────────────────────────────────────────────
        detected_funds = []
        for alias, full_name in FUND_ALIASES.items():
            if alias in q:
                if full_name not in detected_funds:
                    detected_funds.append(full_name)

        # ── Section routing ───────────────────────────────────────────────────
        section_scores: dict[str, int] = {}
        for keyword, sections in SECTION_ROUTING.items():
            if keyword in q:
                for i, sec in enumerate(sections):
                    section_scores[sec] = section_scores.get(sec, 0) + (2 - i)

        # Sort by score, default to overview if no match
        ordered_sections = sorted(section_scores, key=section_scores.get, reverse=True)
        if not ordered_sections:
            ordered_sections = ["overview"]

        # ── Comparative / cross-fund detection ────────────────────────────────
        comparative_kws = ["compare", " vs ", "versus", "all funds", "which fund", "best fund"]
        is_comparative = any(kw in q for kw in comparative_kws) or len(detected_funds) > 1

        # ── Top-K logic ───────────────────────────────────────────────────────
        if is_comparative:
            top_k = 5   # one per fund
        elif "holdings" in ordered_sections:
            top_k = 3   # sector-batched, need a few
        else:
            top_k = 3   # single-fact queries need 1-3

        return {
            "detected_funds":  detected_funds,
            "fund_filter":     detected_funds[0] if len(detected_funds) == 1 else None,
            "section_hints":   ordered_sections[:3],   # top-3 section targets
            "is_comparative":  is_comparative,
            "top_k":           top_k,
        }
```

**`retriever/retriever.py`** — two-stage filtered retriever:

```python
from embeddings.embedder import BGEEmbedder
from vectorstore.store import VectorStore
from retriever.intent_detector import IntentDetector
from config.settings import TOP_K

class FundRetriever:
    """
    Two-stage retriever:
      1. IntentDetector classifies query → fund_filter + section_hints + top_k
      2. ChromaDB filtered vector search (metadata pre-filter → vector similarity)
      3. Post-rank: deduplicate, sort by distance
    """

    def __init__(self, top_k: int = TOP_K):
        self.embedder = BGEEmbedder()
        self.store    = VectorStore()
        self.detector = IntentDetector()
        self.default_top_k = top_k

    def retrieve(self, query: str, debug: bool = False) -> list[dict]:
        """
        Retrieve the most relevant chunks for a query.

        Args:
            query: User's natural language question.
            debug: If True, also return intent detection result.

        Returns:
            List of chunk dicts: {content, metadata, distance, score}
            Ordered by relevance (ascending distance = more similar).
        """
        # Stage 1: Detect intent
        intent = self.detector.detect(query)
        top_k  = intent["top_k"] or self.default_top_k

        # Stage 2: Build ChromaDB where= filter
        where = self._build_filter(intent)

        # Stage 3: Embed + vector search
        q_vec = self.embedder.embed_query(query)

        # Primary search: with filter
        results = self.store.query(q_vec, n_results=top_k, where=where if where else None)

        chunks = self._parse_results(results)

        # Fallback: if filtered search returns < 2 results, widen to no filter
        if len(chunks) < 2:
            results = self.store.query(q_vec, n_results=self.default_top_k)
            chunks = self._parse_results(results)

        # Stage 4: Post-rank — deduplicate same content, sort by distance
        chunks = self._deduplicate(chunks)
        chunks.sort(key=lambda x: x["distance"])

        if debug:
            return chunks, intent
        return chunks

    def _build_filter(self, intent: dict) -> dict | None:
        """Build a ChromaDB where= filter dict from intent."""
        fund_filter    = intent.get("fund_filter")
        section_hints  = intent.get("section_hints", [])
        is_comparative = intent.get("is_comparative", False)

        conditions = []

        # Fund pre-filter (only when exactly one fund is named)
        if fund_filter and not is_comparative:
            conditions.append({"fund_name": fund_filter})

        # Section pre-filter (only when section hint is very specific — 1 section)
        if len(section_hints) == 1 and not is_comparative:
            conditions.append({"section": section_hints[0]})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _parse_results(self, results: dict) -> list[dict]:
        """Parse raw ChromaDB result dict into list of chunk dicts."""
        chunks = []
        docs   = results.get("documents", [[]])[0]
        metas  = results.get("metadatas", [[]])[0]
        dists  = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            chunks.append({
                "content":  doc,
                "metadata": meta,
                "distance": dist,
                "score":    round(1 - dist, 4),  # cosine similarity: 1 - distance
            })
        return chunks

    def _deduplicate(self, chunks: list[dict]) -> list[dict]:
        """Remove duplicate chunks (same fund_slug + section + chunk_index)."""
        seen = set()
        unique = []
        for c in chunks:
            m = c["metadata"]
            key = (m.get("fund_slug"), m.get("section"), m.get("chunk_index"))
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique
```

#### Retrieval Behaviour by Query Type

| Query | Intent Result | Filter Applied | Expected Top-1 |
|---|---|---|---|
| `"NAV of HDFC Mid Cap Fund"` | fund=Mid Cap, section=overview | `fund_name + section` | overview chunk, dist < 0.15 |
| `"3Y returns of HDFC Gold ETF"` | fund=Gold, section=returns | `fund_name + section` | returns chunk |
| `"Compare 5Y returns all funds"` | comparative=True, k=5 | no filter | 5 × returns chunks |
| `"Exit load HDFC Silver ETF"` | fund=Silver, section=exit_load_tax | `fund_name + section` | exit_load_tax chunk |
| `"Top holdings HDFC Small Cap"` | fund=Small Cap, section=holdings | `fund_name` | holdings chunk, Financial sector |
| `"How to invest in Mid Cap"` | fund=Mid Cap, section=faq | `fund_name + section` | faq chunk |
| `"Expense ratio"` (no fund named) | no fund, section=overview | no filter → all 5 | 5 × overview chunks |

#### Top-K Decision Table

| Scenario | Recommended k | Rationale |
|---|---|---|
| Single fund, single fact (NAV, expense) | 3 | 1 exact match + 2 context chunks |
| Single fund, multi-fact (returns + rank) | 3 | returns + performance_ranking chunks |
| Cross-fund comparison | 5 | 1 chunk per fund for the section |
| Holdings query | 3 | 2–3 sector batches cover most queries |
| FAQ / procedural | 3 | 1 exact Q&A + 2 related FAQs |
| Open-ended qualitative | 5 | about_fund + faq + performance combined |

### 3.2 Build Prompt Builder

**`llm/prompt_builder.py`:**

```python
SYSTEM_PROMPT = """You are an expert mutual fund assistant specializing in HDFC Mutual Fund schemes.
You answer questions about 5 specific HDFC funds based ONLY on the provided context from Groww.in data.

RULES:
1. Answer ONLY using the provided context. Do NOT use outside knowledge.
2. If the answer is not in the context, say "I don't have this information in my knowledge base."
3. Always mention the specific fund name(s) in your answer.
4. Use bullet points or tables for structured data.
5. Do NOT provide financial advice. Add a disclaimer when discussing returns or risk.
6. Be concise and accurate.
7. When comparing funds, present data side by side.

The 5 funds you know about are:
- HDFC Gold ETF Fund of Fund Direct Plan Growth
- HDFC Large Cap Fund Direct Growth
- HDFC Small Cap Fund Direct Growth
- HDFC Silver ETF FoF Direct Growth
- HDFC Mid Cap Fund Direct Growth
"""

def build_prompt(query: str, retrieved_chunks: list[dict]) -> str:
    context = "\n\n---\n\n".join([
        f"[Source: {chunk['metadata'].get('fund_name', 'Unknown')}]\n{chunk['content']}"
        for chunk in retrieved_chunks
    ])

    return f"""{SYSTEM_PROMPT}

CONTEXT:
{context}

USER QUESTION:
{query}

ANSWER:"""
```

### 3.3 Build Groq LLM Generator

**`llm/generator.py`:**

```python
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

class GroqGenerator:
    def __init__(
        self,
        model: str = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ):
        self.llm = ChatGroq(
            model=model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            temperature=temperature,
            max_tokens=max_tokens,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
```

> **Why Groq?**
> - Free tier available with generous rate limits.
> - LPU hardware delivers **~500 tokens/sec** — 10–20x faster than GPU inference.
> - Hosts open-source models like `llama-3.1-8b-instant`, `mixtral-8x7b`, `gemma2-9b-it`.
> - LangChain has first-class Groq integration via `langchain-groq`.

### 3.4 Build Query Pipeline Orchestrator

**`pipeline/query.py`:**

```python
from retriever.retriever import FundRetriever
from llm.prompt_builder import build_prompt
from llm.generator import GroqGenerator

class QueryPipeline:
    def __init__(self):
        self.retriever = FundRetriever(top_k=5)
        self.generator = GroqGenerator()

    def run(self, user_query: str) -> dict:
        # Step 1: Retrieve relevant chunks
        retrieved = self.retriever.retrieve(user_query)

        # Step 2: Build prompt with context
        prompt = build_prompt(user_query, retrieved)

        # Step 3: Generate answer via Groq
        answer = self.generator.generate(prompt)

        # Step 4: Collect source URLs
        source_urls = list(set(
            chunk["metadata"].get("source_url", "")
            for chunk in retrieved
        ))
        source_funds = list(set(
            chunk["metadata"].get("fund_name", "")
            for chunk in retrieved
        ))

        return {
            "answer": answer,
            "source_urls": source_urls,
            "source_funds": source_funds,
            "num_chunks_retrieved": len(retrieved),
        }

# Quick test
if __name__ == "__main__":
    pipeline = QueryPipeline()
    result = pipeline.run("What is the NAV of HDFC Mid Cap Fund?")
    print(result["answer"])
    print(f"\nSources: {result['source_urls']}")
```

### Phase 3 Deliverables

| # | Deliverable | Verification |
|---|-------------|-------------|
| 1 | Retriever returns relevant chunks | Top-3 chunks are from the correct fund |
| 2 | Prompt builder formats correctly | Prompt includes system instruction + context + query |
| 3 | Groq LLM generates answers | `generator.generate(prompt)` returns a coherent answer |
| 4 | Query pipeline works end-to-end | `python -m pipeline.query` answers fund questions correctly |

### Phase 3 Test

```python
# tests/test_retriever.py
def test_retrieval_relevance():
    from retriever.retriever import FundRetriever
    retriever = FundRetriever(top_k=3)
    results = retriever.retrieve("HDFC Mid Cap Fund expense ratio")
    assert len(results) == 3
    # At least one chunk should mention Mid Cap
    assert any("Mid Cap" in r["content"] for r in results)

# tests/test_e2e.py
def test_full_query_pipeline():
    from pipeline.query import QueryPipeline
    pipeline = QueryPipeline()
    result = pipeline.run("What is the expense ratio of HDFC Gold ETF FoF?")
    assert "0.20" in result["answer"] or "expense" in result["answer"].lower()
    assert len(result["source_urls"]) > 0
```

---

## Phase 4: REST API Backend (FastAPI)

> **Goal:** Expose the RAG query pipeline as a production-grade REST API so the frontend can communicate cleanly with the backend.
> **Duration:** ~2 days

### 4.1 Architecture Overview

```
Frontend (Next.js)  ──────►  FastAPI Backend  ──────►  RAG Pipeline
   Port 3000                   Port 8000               (BGE + ChromaDB + Groq)
   /chat                       POST /api/chat
   /funds                      GET  /api/funds
   /health                     GET  /api/health
```

**Why FastAPI over direct Streamlit?**
- Clean separation of concerns: UI ↔ API ↔ RAG logic
- The frontend can call the API via `fetch()` / `axios` — no Python in the browser
- Swagger docs at `/docs` for free
- Async support: multiple concurrent chat requests
- Enables future mobile/CLI clients without changing the RAG logic

### 4.2 API Design

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/health` | Liveness check — returns status + chunk count | None |
| `GET` | `/api/funds` | List all 5 covered funds + basic metadata | None |
| `POST` | `/api/chat` | Main chat endpoint — query → answer + sources | None |
| `GET` | `/api/chat/history/{session_id}` | Retrieve conversation history | None |

### 4.3 Request / Response Schemas

**`POST /api/chat` — Request:**
```json
{
  "query": "What is the NAV of HDFC Mid Cap Fund?",
  "session_id": "user-abc123",
  "debug": false
}
```

**`POST /api/chat` — Response:**
```json
{
  "answer": "The NAV of HDFC Mid Cap Fund Direct Growth is ₹226.92 (as of 2026-06-28).",
  "query": "What is the NAV of HDFC Mid Cap Fund?",
  "session_id": "user-abc123",
  "source_funds": ["HDFC Mid Cap Fund Direct Growth"],
  "source_sections": ["overview"],
  "source_urls": ["https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"],
  "num_chunks": 3,
  "context_summary": "3 chunks from: HDFC Mid Cap Fund Direct Growth (overview, returns)",
  "model": "llama-3.1-8b-instant",
  "input_tokens": 842,
  "output_tokens": 67,
  "response_time_ms": 1230
}
```

**`GET /api/funds` — Response:**
```json
{
  "funds": [
    {
      "name": "HDFC Mid Cap Fund Direct Growth",
      "slug": "hdfc-mid-cap-fund-direct-growth",
      "category": "Equity",
      "sub_category": "Mid Cap",
      "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    },
    ...
  ],
  "total": 5
}
```

### 4.4 Implementation

**`app/api.py`** — FastAPI application:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import time
import uuid

from pipeline.query import QueryPipeline
from config.settings import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR

app = FastAPI(
    title="HDFC Mutual Fund RAG API",
    description="RAG-powered chatbot API for 5 HDFC Mutual Fund schemes",
    version="1.0.0",
)

# Allow requests from Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store (replace with Redis for prod) ─────────────────────
_sessions: dict[str, list[dict]] = {}

# ── Singleton pipeline (load once at startup) ─────────────────────────────────
_pipeline: QueryPipeline | None = None

@app.on_event("startup")
async def startup_event():
    global _pipeline
    print("Loading RAG pipeline...")
    _pipeline = QueryPipeline()
    print("Pipeline ready.")

# ── Schemas ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str         = Field(..., min_length=3, max_length=500)
    session_id: str    = Field(default_factory=lambda: str(uuid.uuid4()))
    debug: bool        = False

class ChatResponse(BaseModel):
    answer:           str
    query:            str
    session_id:       str
    source_funds:     list[str]
    source_sections:  list[str]
    source_urls:      list[str]
    num_chunks:       int
    context_summary:  str
    model:            str
    input_tokens:     int
    output_tokens:    int
    response_time_ms: int

class FundInfo(BaseModel):
    name:         str
    slug:         str
    category:     str
    sub_category: str
    url:          str

class FundsResponse(BaseModel):
    funds: list[FundInfo]
    total: int

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    from vectorstore.store import VectorStore
    store = VectorStore()
    return {
        "status": "ok",
        "pipeline_loaded": _pipeline is not None,
        "chunks_in_db": store.count(),
        "collection": CHROMA_COLLECTION_NAME,
    }

@app.get("/api/funds", response_model=FundsResponse)
async def get_funds():
    funds = [
        FundInfo(
            name="HDFC Mid Cap Fund Direct Growth",
            slug="hdfc-mid-cap-fund-direct-growth",
            category="Equity", sub_category="Mid Cap",
            url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        ),
        FundInfo(
            name="HDFC Large Cap Fund Direct Growth",
            slug="hdfc-large-cap-fund-direct-growth",
            category="Equity", sub_category="Large Cap",
            url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        ),
        FundInfo(
            name="HDFC Small Cap Fund Direct Growth",
            slug="hdfc-small-cap-fund-direct-growth",
            category="Equity", sub_category="Small Cap",
            url="https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        ),
        FundInfo(
            name="HDFC Gold ETF Fund of Fund Direct Plan Growth",
            slug="hdfc-gold-etf-fund-of-fund-direct-plan-growth",
            category="Commodity", sub_category="Gold",
            url="https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
        ),
        FundInfo(
            name="HDFC Silver ETF FoF Direct Growth",
            slug="hdfc-silver-etf-fof-direct-growth",
            category="Commodity", sub_category="Silver",
            url="https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
        ),
    ]
    return FundsResponse(funds=funds, total=len(funds))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if _pipeline is None:
        raise HTTPException(503, "Pipeline not ready. Try again in a few seconds.")

    t0 = time.time()
    try:
        result = _pipeline.run(req.query, debug=req.debug)
    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {str(e)}")

    elapsed_ms = int((time.time() - t0) * 1000)

    # Persist to session history
    _sessions.setdefault(req.session_id, []).append({
        "role": "user",      "content": req.query,
    })
    _sessions[req.session_id].append({
        "role": "assistant", "content": result["answer"],
    })

    return ChatResponse(
        answer           = result["answer"],
        query            = req.query,
        session_id       = req.session_id,
        source_funds     = result["source_funds"],
        source_sections  = result["source_sections"],
        source_urls      = result["source_urls"],
        num_chunks       = result["num_chunks"],
        context_summary  = result["context_summary"],
        model            = result["model"],
        input_tokens     = result["input_tokens"],
        output_tokens    = result["output_tokens"],
        response_time_ms = elapsed_ms,
    )

@app.get("/api/chat/history/{session_id}")
async def get_history(session_id: str):
    history = _sessions.get(session_id, [])
    return {"session_id": session_id, "messages": history, "count": len(history)}
```

**Run the API:**
```bash
pip install fastapi uvicorn
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
# Swagger UI: http://localhost:8000/docs
```

### 4.5 Phase 4 Deliverables & Tests

| # | Deliverable | Verification |
|---|-------------|-------------|
| 1 | API server starts | `GET /api/health` returns `{"status": "ok"}` |
| 2 | Funds endpoint works | `GET /api/funds` returns all 5 fund names |
| 3 | Chat endpoint answers | `POST /api/chat` returns a non-empty `answer` |
| 4 | CORS configured | Frontend on port 3000 can call API on port 8000 |
| 5 | Session history stored | `GET /api/chat/history/{id}` returns past messages |
| 6 | Swagger UI available | `/docs` renders interactive API docs |

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_funds_returns_five():
    r = client.get("/api/funds")
    assert r.status_code == 200
    assert r.json()["total"] == 5

def test_chat_endpoint():
    r = client.post("/api/chat", json={"query": "What is the NAV of HDFC Mid Cap Fund?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["num_chunks"] >= 1
    assert body["response_time_ms"] > 0
```

---

## Phase 5: Premium Next.js Frontend

> **Goal:** Build a beautiful, production-quality chat UI that consumes the Phase 4 FastAPI backend.
> **Duration:** ~2.5 days

### 5.1 Design System

**Visual identity:**
- **Theme:** Deep dark mode with glassmorphism cards
- **Primary:** `#6C63FF` (electric indigo) — accent color
- **Surface:** `rgba(255,255,255,0.05)` frosted glass cards
- **Background:** `#0A0A1A` dark navy
- **Text:** `#E8E8F0` primary, `#8888AA` muted
- **Font:** `Inter` (body) + `Outfit` (headings) from Google Fonts
- **Accent gradient:** `135deg, #6C63FF → #A855F7` (indigo → purple)

**Design patterns:**
- Glassmorphism panels with `backdrop-filter: blur(20px)`
- Subtle animated gradient background (`@keyframes gradientShift`)
- Smooth message slide-in animations (`@keyframes slideUp`)
- Typing indicator (bouncing dots) during answer generation
- Section-aware source badges (color-coded by section type)

### 5.2 Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout (fonts, global CSS)
│   │   ├── page.tsx            # Main chat page
│   │   └── globals.css         # Design system + animations
│   ├── components/
│   │   ├── ChatInterface.tsx   # Main chat container
│   │   ├── MessageBubble.tsx   # User / assistant message
│   │   ├── TypingIndicator.tsx # Animated "..." while waiting
│   │   ├── SourceCard.tsx      # Source attribution card
│   │   ├── FundSidebar.tsx     # Fund list + quick-ask chips
│   │   ├── QueryChips.tsx      # Suggested query buttons
│   │   └── StatsBar.tsx        # Token count + response time
│   ├── hooks/
│   │   ├── useChat.ts          # Chat state + API calls
│   │   └── useSession.ts       # Session ID management
│   └── lib/
│       └── api.ts              # FastAPI client (typed fetch)
├── next.config.js
└── package.json
```

### 5.3 API Client

**`frontend/src/lib/api.ts`:**
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatResponse {
  answer:           string;
  query:            string;
  session_id:       string;
  source_funds:     string[];
  source_sections:  string[];
  source_urls:      string[];
  num_chunks:       number;
  context_summary:  string;
  model:            string;
  input_tokens:     number;
  output_tokens:    number;
  response_time_ms: number;
}

export async function sendMessage(
  query: string,
  sessionId: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ query, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getFunds() {
  const res = await fetch(`${API_BASE}/api/funds`);
  return res.json();
}
```

### 5.4 Core Components

**`MessageBubble.tsx`** — renders user and assistant messages:
```tsx
// User bubble: right-aligned, indigo gradient
// Assistant bubble: left-aligned, glass card
// Supports markdown rendering (react-markdown)
// Fade + slide animation on mount
// Shows fund name badge if source is identified
```

**`FundSidebar.tsx`** — left sidebar with fund info:
```tsx
// Lists all 5 funds with category badge (Equity / Commodity)
// Click to inject a quick query ("Tell me about HDFC Mid Cap Fund")
// Shows scraped_at date from API
// Collapsible on mobile
```

**`QueryChips.tsx`** — suggested questions:
```tsx
// Grid of clickable question chips
// Pre-populated: "NAV of Mid Cap?", "Compare all returns", "Exit load?"
// Disappears after first message is sent
// Smooth fade-out animation
```

**`SourceCard.tsx`** — source attribution below answers:
```tsx
// Shows each source chunk: fund name + section badge
// Section badges color-coded: overview=blue, returns=green, faq=purple
// Expandable to show full chunk content
// Links to Groww.in source URL
```

**`StatsBar.tsx`** — response metadata footer:
```tsx
// Shows: model name | tokens in/out | response time | num chunks
// Subtle, muted style — informative but not distracting
```

### 5.5 Key UI States & Interactions

| State | Visual Treatment |
|---|---|
| Initial / empty | Welcome screen with animated logo + query chips |
| Typing query | Input box glows with indigo border |
| Waiting for answer | Typing indicator (3 bouncing dots) + loading blur on input |
| Answer received | Message slides in + source cards fade in below |
| Error | Red glass card with retry button |
| Comparative answer | Table rendered in markdown with alternating row colors |

### 5.6 Setup & Run

```bash
# One-time setup
npx create-next-app@latest frontend --typescript --tailwind=false --eslint --app
cd frontend
npm install react-markdown remark-gfm framer-motion

# Dev server (run alongside FastAPI backend)
npm run dev
# App: http://localhost:3000
```

**Environment variable:**
```
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 5.7 Phase 5 Deliverables

| # | Deliverable | Verification |
|---|-------------|-------------|
| 1 | Chat UI renders in dark mode | Open `localhost:3000` — gradient background, glass cards visible |
| 2 | Send a query and get a response | Type question → typing indicator → answer fades in |
| 3 | Source cards shown | Each answer has colored section badges + Groww links |
| 4 | Suggested query chips | First load shows clickable suggested questions |
| 5 | Fund sidebar lists 5 funds | Left panel shows all funds with category tags |
| 6 | Mobile responsive | Sidebar collapses on small screens; chat still usable |
| 7 | Stats bar shows metadata | Token count + response time visible under each answer |
| 8 | Markdown renders correctly | Tables (from comparison queries) display properly |

### 5.8 Phase 5 Tests

```typescript
// frontend/src/__tests__/api.test.ts
describe("API client", () => {
  it("sendMessage returns a ChatResponse", async () => {
    const result = await sendMessage("What is the NAV of HDFC Mid Cap Fund?", "test-session");
    expect(result.answer).toBeTruthy();
    expect(result.source_funds.length).toBeGreaterThan(0);
    expect(result.response_time_ms).toBeGreaterThan(0);
  });
});

// frontend/src/__tests__/components.test.tsx
describe("MessageBubble", () => {
  it("renders user message correctly", () => {
    render(<MessageBubble role="user" content="Test query" />);
    expect(screen.getByText("Test query")).toBeInTheDocument();
  });

  it("renders assistant message with markdown", () => {
    render(<MessageBubble role="assistant" content="**Bold text** and a table" />);
    expect(screen.getByText(/Bold text/)).toBeInTheDocument();
  });
});
```

---

## Phase 6: Scheduled Daily Ingestion (GitHub Actions)

> **Goal:** Automate the ingestion pipeline to run once daily via GitHub Actions, ensuring the vector store always has the latest fund data from Groww.in without adding latency to user queries.
> **Duration:** ~1 day

### 6.1 Design Rationale

The ingestion pipeline (scrape → extract → chunk → embed → store) is **expensive** (~2 min, requires Selenium + BGE model). Running it on every user query would add unacceptable latency. Instead, we decouple ingestion from querying:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DECOUPLED ARCHITECTURE                         │
│                                                                         │
│   ┌──────────────────────┐          ┌──────────────────────┐           │
│   │  SCHEDULER (Offline) │          │   QUERY (Online)     │           │
│   │                      │          │                      │           │
│   │  GitHub Actions      │          │  User → FastAPI →    │           │
│   │  cron: daily 2:00 AM │   ──▶    │  ChromaDB → Groq →   │           │
│   │                      │  pushes  │  Response            │           │
│   │  Scrape → Chunk →    │  updated │                      │           │
│   │  Embed → ChromaDB    │  DB      │  (NO ingestion here, │           │
│   │                      │          │   just vector search) │           │
│   └──────────────────────┘          └──────────────────────┘           │
│                                                                         │
│   Runs: Once/day at 2:00 AM IST    Runs: Every user query              │
│   Duration: ~2 minutes              Duration: <3 seconds               │
│   Cost: Free (GitHub Actions)       Cost: Groq API (free tier)         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key principle:** The ingestion pipeline runs **only once per day** (via scheduled GitHub Actions), not on every user query. This keeps query latency under 3 seconds while ensuring data freshness (NAV, AUM, holdings update daily on Groww).

### 6.2 GitHub Actions Workflow

**`.github/workflows/daily-ingestion.yml`:**

```yaml
name: Daily Data Ingestion

on:
  schedule:
    # Run daily at 2:00 AM IST (8:30 PM UTC previous day)
    - cron: '30 20 * * *'
  workflow_dispatch:  # Allow manual trigger from GitHub UI

jobs:
  ingest:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Install Chrome for Selenium
        uses: browser-actions/setup-chrome@v1
        with:
          chrome-version: 'stable'

      - name: Run ingestion pipeline
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          CHROMA_PERSIST_DIR: ./chroma_db
        run: |
          python -m pipeline.ingest

      - name: Verify ingestion
        run: |
          python -c "
          from vectorstore.store import VectorStore
          from config.settings import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR
          store = VectorStore(collection_name=CHROMA_COLLECTION_NAME, persist_dir=CHROMA_PERSIST_DIR)
          count = store.count()
          print(f'✓ ChromaDB has {count} chunks')
          assert count >= 100, f'Expected >=100 chunks, got {count}'
          "

      - name: Commit updated ChromaDB
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add chroma_db/
          git diff --staged --quiet || git commit -m "chore: daily data refresh $(date -u +%Y-%m-%d)"
          git push

      - name: Trigger Railway redeploy (optional)
        if: success()
        run: |
          if [ -n "${{ secrets.RAILWAY_WEBHOOK_URL }}" ]; then
            curl -X POST "${{ secrets.RAILWAY_WEBHOOK_URL }}"
            echo "✓ Railway redeploy triggered"
          else
            echo "⚠ RAILWAY_WEBHOOK_URL not set, skipping redeploy"
          fi
```

### 6.3 Ingestion Guard Script

To prevent accidental ingestion during query time, add a guard to the backend:

**Update `pipeline/ingest.py`** — add a lock file mechanism:

```python
import os
import sys
from datetime import datetime

LOCK_FILE = os.path.join(os.path.dirname(__file__), ".ingestion_lock")
LAST_RUN_FILE = os.path.join(os.path.dirname(__file__), ".last_ingestion")

def is_ingestion_needed() -> bool:
    """Check if ingestion should run (not run in last 20 hours)."""
    if not os.path.exists(LAST_RUN_FILE):
        return True
    with open(LAST_RUN_FILE) as f:
        last_run = datetime.fromisoformat(f.read().strip())
    hours_since = (datetime.now() - last_run).total_seconds() / 3600
    return hours_since >= 20  # Allow re-run after 20h (buffer for cron drift)

def mark_ingestion_complete():
    """Record the timestamp of successful ingestion."""
    with open(LAST_RUN_FILE, "w") as f:
        f.write(datetime.now().isoformat())

def run_ingestion():
    if not is_ingestion_needed():
        print("⏭  Ingestion skipped — last run was less than 20 hours ago.")
        return

    # ... existing ingestion logic ...

    mark_ingestion_complete()
    print("✓ Ingestion complete. Next run allowed after 20 hours.")
```

### 6.4 Required GitHub Secrets

| Secret | Purpose | Where to get it |
|---|---|---|
| `GROQ_API_KEY` | LLM API key for embedding/query | [console.groq.com](https://console.groq.com) |
| `RAILWAY_WEBHOOK_URL` | (Optional) Trigger Railway redeploy after DB update | Railway dashboard → Deploy → Webhook |

### 6.5 Monitoring & Failure Handling

| Scenario | Handling |
|---|---|
| Scraper fails (Groww down) | GitHub Actions retries once; if both fail, the old ChromaDB persists (stale but functional) |
| Embedding model download fails | `pip cache` in workflow ensures model is cached across runs |
| ChromaDB corruption | `store.reset()` in `ingest.py` wipes and rebuilds from scratch each run |
| Workflow failure notification | GitHub sends email notification on workflow failure by default |
| Manual re-run needed | Click "Run workflow" in GitHub Actions UI (enabled by `workflow_dispatch`) |

### 6.6 Phase 6 Deliverables

| # | Deliverable | Verification |
|---|-------------|-------------|
| 1 | GitHub Actions workflow file created | `.github/workflows/daily-ingestion.yml` exists |
| 2 | Workflow runs on schedule | Cron triggers at 2:00 AM IST daily |
| 3 | Manual trigger works | "Run workflow" button in GitHub Actions UI |
| 4 | Ingestion completes in CI | Logs show `✓ ChromaDB has 128 chunks` |
| 5 | Updated DB is committed | Git log shows daily `chore: daily data refresh` commits |
| 6 | Ingestion guard prevents double-runs | Running `python -m pipeline.ingest` twice skips second run |
| 7 | Query latency unaffected | User queries still respond in <3 seconds |

### 6.7 Phase 6 Test

```bash
# Test 1: Manual trigger from CLI
python -m pipeline.ingest
# Expected: Full ingestion runs, ChromaDB updated

# Test 2: Run again immediately
python -m pipeline.ingest
# Expected: "Ingestion skipped — last run was less than 20 hours ago."

# Test 3: Verify query latency is unaffected
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "NAV of HDFC Mid Cap?"}'
# Expected: response_time_ms < 3000
```

---

## Full Timeline Summary

| Phase | Module | Tasks | Duration | Status |
|-------|--------|-------|----------|--------|
| **Phase 1** | Scraper + Extractor | Setup, Selenium scraper, `__NEXT_DATA__` extractor | ~2 days | ✅ Done |
| **Phase 2** | Chunker + Embedder + ChromaDB | `SectionAwareChunker`, BGE-small, ChromaDB ingest | ~2 days | ✅ Done |
| **Phase 3** | Retriever + LLM + Pipeline | `IntentDetector`, `FundRetriever`, Groq, `QueryPipeline` | ~2 days | ✅ Done |
| **Phase 4** | FastAPI Backend | REST API, CORS, session history, Pydantic schemas | ~2 days | ⬜ Next |
| **Phase 5** | Next.js Frontend | Dark glass UI, chat interface, source cards, mobile | ~2.5 days | ⬜ Next |
| **Phase 6** | Scheduler (GitHub Actions) | Daily cron workflow, ingestion guard, Railway redeploy | ~1 day | ⬜ Planned |
| | | **Total** | **~11.5 days** | |

---

## Key Commands Quick Reference

```bash
# Setup
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

# Phase 2: Re-extract + chunk (if HTML already scraped)
python scripts/run_phase2.py

# Phase 2: Ingest chunks into ChromaDB
python -m pipeline.ingest

# Phase 3: Test the query pipeline
python -m pipeline.query --query "NAV of HDFC Mid Cap?" --debug

# Phase 4: Start the FastAPI backend
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

# Phase 5: Start the Next.js frontend (in /frontend)
npm run dev

# Phase 6: Manually trigger ingestion (or let GitHub Actions cron handle it)
python -m pipeline.ingest

# Tests (all phases)
pytest tests/ -v

# Tests (skip LLM calls)
pytest tests/ -v -k "not TestQueryPipeline"
```

---

## Technology Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **LLM Provider** | **Groq** (`llama-3.1-8b-instant`) | Free tier, ~500 tok/sec via LPU |
| **Embedding Model** | **BGE** (`BAAI/bge-small-en-v1.5`) | Free, local, 384-dim, no API key |
| **Vector Store** | **ChromaDB** | Local, persistent, metadata filtering |
| **Data Source** | **Groww.in** (5 URLs) | `__NEXT_DATA__` JSON for reliable extraction |
| **Backend** | **FastAPI + Uvicorn** | Async, typed, Swagger UI for free |
| **Frontend** | **Next.js (App Router)** | TypeScript, SSR, fast, modern React |
| **Frontend Styling** | **Vanilla CSS** (CSS Modules) | Full control, glassmorphism, animations |
| **Scraper** | **Selenium** | Required for JS-rendered Groww pages |


