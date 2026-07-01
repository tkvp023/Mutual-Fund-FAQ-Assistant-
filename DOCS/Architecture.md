# Architecture: RAG-based Mutual Fund FAQ Chatbot

> **Reference:** [problemStatement.md](file:///c:/Users/THARUN/Videos/RAG-based%20Mutual%20Fund%20FAQ%20Chatbot/DOCS/problemStatement.md)
> **Last Updated:** June 2026

---

## 1. System Overview

The RAG-based Mutual Fund FAQ Chatbot is a **question-answering system** that uses Retrieval-Augmented Generation to provide accurate, grounded responses about 5 specific HDFC Mutual Fund schemes. The system scrapes data exclusively from **Groww.in** fund pages, processes and embeds this data into a vector store, and uses an LLM to generate contextual answers at query time.

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM BOUNDARY                                     │
│                                                                                  │
│  ┌─────────────┐     ┌─────────────────────────────────────────────────────┐     │
│  │             │     │              OFFLINE PIPELINE                       │     │
│  │   Groww.in  │────▶│  Web Scraper ──▶ Text Processor ──▶ Chunker ──▶    │     │
│  │  (5 URLs)   │     │                                     Embedder ──▶   │     │
│  │             │     │                                     Vector Store    │     │
│  └─────────────┘     └──────────────────────────────┬──────────────────────┘     │
│                                                      │                           │
│                                                      ▼                           │
│  ┌─────────────┐     ┌─────────────────────────────────────────────────────┐     │
│  │             │     │              ONLINE PIPELINE                        │     │
│  │    User     │────▶│  Chat UI ──▶ Query Encoder ──▶ Retriever ──▶       │     │
│  │  (Browser)  │◀────│             Prompt Builder ──▶ LLM ──▶ Response    │     │
│  │             │     │                                                     │     │
│  └─────────────┘     └─────────────────────────────────────────────────────┘     │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Grounded Answers** | Every response must be traceable to scraped Groww data, not LLM parametric knowledge. |
| **Single Source of Truth** | Groww.in fund pages are the sole external data source — no PDFs, CSVs, or other documents. |
| **Modularity** | Each component (scraper, embedder, retriever, LLM) is independently replaceable. |
| **Low Latency** | Online query path targets ≤ 5 seconds end-to-end response time. |
| **Extensibility** | Adding new funds = adding new URLs to the scraper config, no code changes required. |

---

## 2. Data Source — Groww.in Fund Pages

The **only external data source** for this system is Groww.in. The following 5 URLs constitute the complete corpus:

| # | Fund Scheme | URL | Category |
|---|-------------|-----|----------|
| 1 | HDFC Gold ETF Fund of Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth | Commodities / Gold |
| 2 | HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth | Equity / Large Cap |
| 3 | HDFC Small Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth | Equity / Small Cap |
| 4 | HDFC Silver ETF FoF Direct Growth | https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth | Commodities / Silver |
| 5 | HDFC Mid Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth | Equity / Mid Cap |

### Data Points Extracted Per URL

```
┌─────────────────────────────────────────────────────┐
│              Groww Fund Page Data Model              │
├─────────────────────────────────────────────────────┤
│                                                      │
│  FUND IDENTITY                                       │
│  ├── Fund Name                                       │
│  ├── Fund House (AMC)                                │
│  ├── Category (Equity / Commodities)                 │
│  ├── Sub-category (Large Cap / Gold / etc.)          │
│  └── Risk Level (High / Very High)                   │
│                                                      │
│  PRICING & SIZE                                      │
│  ├── Latest NAV + NAV Date                           │
│  ├── Fund Size (AUM in ₹ Cr)                        │
│  ├── Expense Ratio (%)                               │
│  └── Minimum SIP Amount (₹)                         │
│                                                      │
│  PERFORMANCE                                         │
│  ├── 1D Return (%)                                   │
│  ├── 1Y / 3Y / 5Y Annualised Returns (%)            │
│  ├── SIP Return History (1Y, 3Y, 5Y)                │
│  └── Groww Star Rating                               │
│                                                      │
│  PORTFOLIO & DETAILS                                 │
│  ├── Top Holdings / Sector Allocation                │
│  ├── Fund Manager Name & Tenure                      │
│  ├── Exit Load Details                               │
│  ├── Tax Implications                                │
│  ├── Peer Comparison Data                            │
│  └── Scheme-Specific FAQ Section                     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 3. Component Architecture

The system is divided into two major pipelines: **Offline (Ingestion)** and **Online (Query)**.

### 3.1 Offline Pipeline — Data Ingestion & Indexing

This pipeline runs periodically (or on-demand) to scrape, process, and index data from the 5 Groww URLs.

```
┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│            │    │              │    │              │    │              │    │              │
│  URL       │───▶│  Web         │───▶│  Content     │───▶│  Text        │───▶│  Embedding   │
│  Config    │    │  Scraper     │    │  Extractor   │    │  Chunker     │    │  Generator   │
│  (5 URLs)  │    │              │    │              │    │              │    │              │
│            │    │              │    │              │    │              │    │              │
└────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                                     │
                                                                                     ▼
                                                                              ┌──────────────┐
                                                                              │              │
                                                                              │  Vector      │
                                                                              │  Store       │
                                                                              │  (ChromaDB / │
                                                                              │   FAISS)     │
                                                                              │              │
                                                                              └──────────────┘
```

#### 3.1.1 URL Config

- **Purpose:** Centralized configuration file holding the 5 Groww URLs.
- **Format:** Python list / JSON / YAML config file.
- **Extensibility:** Adding a new fund = appending a new URL to this config.

```python
# config/fund_urls.py
FUND_URLS = [
    "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
]
```

#### 3.1.2 Web Scraper

- **Purpose:** Fetch raw HTML content from each Groww fund page.
- **Technology Options:**

| Option | Use Case | Pros | Cons |
|--------|----------|------|------|
| `requests` + `BeautifulSoup` | Static HTML content | Lightweight, fast | Won't render JS-loaded content |
| `Selenium` / `Playwright` | JS-rendered pages (Groww uses Next.js) | Renders full DOM | Heavier, slower |
| `requests_html` | Hybrid approach | Async JS rendering | Limited JS support |

- **Recommended:** `Selenium` or `Playwright` since Groww.in is a Next.js app and renders much of its content via JavaScript.

- **Output:** Raw HTML per URL.

```python
# scraper/groww_scraper.py
class GrowwScraper:
    def __init__(self, urls: list[str]):
        self.urls = urls

    def scrape(self, url: str) -> str:
        """Fetch rendered HTML from a Groww fund page."""
        # Uses Selenium/Playwright to render JS
        # Returns full page HTML
        pass

    def scrape_all(self) -> dict[str, str]:
        """Scrape all configured fund URLs."""
        return {url: self.scrape(url) for url in self.urls}
```

#### 3.1.3 Content Extractor

- **Purpose:** Parse raw HTML and extract structured + unstructured text content.
- **Technology:** `BeautifulSoup4` for HTML parsing.
- **Extracts:**
  - Fund metadata (name, category, risk, NAV, AUM, expense ratio, rating)
  - Performance tables (returns data, SIP calculator results)
  - Portfolio / holdings sections
  - Fund manager details
  - FAQ sections
  - Peer comparison tables
- **Output:** Structured text documents (Markdown or plain text) per fund.

```python
# extractor/content_extractor.py
class ContentExtractor:
    def extract(self, html: str, url: str) -> dict:
        """Extract structured fund data from Groww HTML."""
        return {
            "fund_name": "...",
            "category": "...",
            "nav": "...",
            "aum": "...",
            "expense_ratio": "...",
            "returns": {...},
            "holdings": [...],
            "raw_text": "...",       # Full page text for chunking
            "source_url": url,
            "scraped_at": "...",     # Timestamp
        }
```

#### 3.1.4 Text Chunker

- **Purpose:** Split extracted text into smaller, semantically meaningful chunks for embedding.
- **Technology:** LangChain's `RecursiveCharacterTextSplitter` or similar.
- **Strategy:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `chunk_size` | 500–1000 chars | Balances context and granularity |
| `chunk_overlap` | 100–200 chars | Preserves context across chunk boundaries |
| `separators` | `["\n\n", "\n", ". ", " "]` | Respects paragraph and sentence boundaries |

- **Metadata attached to each chunk:**
  - `fund_name` — Which fund this chunk belongs to
  - `source_url` — The Groww URL it was scraped from
  - `section` — Which part of the page (e.g., "returns", "holdings", "overview")
  - `scraped_at` — Timestamp of last scrape

```python
# chunker/text_chunker.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

class FundTextChunker:
    def __init__(self, chunk_size=800, chunk_overlap=150):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " "],
        )

    def chunk(self, text: str, metadata: dict) -> list[dict]:
        """Split text into chunks with metadata."""
        chunks = self.splitter.split_text(text)
        return [
            {"content": chunk, "metadata": metadata}
            for chunk in chunks
        ]
```

#### 3.1.5 Embedding Generator

- **Purpose:** Convert text chunks into dense vector representations for semantic search.
- **Technology:** `BAAI/bge-small-en-v1.5` (BGE — Beijing Academy of AI General Embedding)

| Model | Dimensions | Provider | Cost | MTEB Rank |
|-------|-----------|----------|------|----------|
| **`BAAI/bge-small-en-v1.5`** ✅ | 384 | HuggingFace (free) | Free / local | Top-tier for size |
| `BAAI/bge-base-en-v1.5` | 768 | HuggingFace (free) | Free / local | Higher accuracy |
| `BAAI/bge-large-en-v1.5` | 1024 | HuggingFace (free) | Free / local | Best accuracy |

- **Selected:** `BAAI/bge-small-en-v1.5` — best balance of accuracy, speed, and memory for a 5-fund corpus. Free, runs locally, no API key required.
- **Note:** BGE models expect a query prefix `"Represent this sentence: "` for optimal retrieval. LangChain's `HuggingFaceBgeEmbeddings` handles this automatically.

#### 3.1.6 Vector Store

- **Purpose:** Persist embeddings and enable fast similarity search at query time.
- **Technology Options:**

| Store | Type | Pros | Cons |
|-------|------|------|------|
| **ChromaDB** | Embedded / Local | Easy setup, persistent, metadata filtering | Single-machine only |
| **FAISS** | In-memory / Local | Very fast search, Facebook-backed | No built-in persistence, needs wrapper |
| **Pinecone** | Cloud-managed | Scalable, fully managed | Costs money, requires internet |

- **Recommended:** `ChromaDB` for this project (local, persistent, supports metadata filtering, works well with LangChain).

```python
# vectorstore/store.py
import chromadb

class VectorStore:
    def __init__(self, collection_name="hdfc_funds"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, chunks: list[dict], embeddings: list[list[float]]):
        """Add embedded chunks to the vector store."""
        pass

    def query(self, query_embedding: list[float], n_results=5) -> list[dict]:
        """Retrieve top-k similar chunks."""
        pass
```

---

### 3.2 Online Pipeline — Query Processing & Response Generation

This pipeline handles real-time user queries through the chat interface.

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│          │    │              │    │              │    │              │    │              │
│  User    │───▶│  Chat UI     │───▶│  Query       │───▶│  Retriever   │───▶│  Prompt      │
│  Query   │    │  (Streamlit/ │    │  Encoder     │    │  (Top-K      │    │  Builder     │
│          │    │   Gradio)    │    │              │    │   Similarity) │    │              │
└──────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                                   │
                       ┌──────────────┐    ┌──────────────┐                        │
                       │              │    │              │                        │
                       │  Formatted   │◀───│  LLM         │◀───────────────────────┘
                       │  Response    │    │  (GPT /      │
                       │  + Sources   │    │   Gemini)    │
                       │              │    │              │
                       └──────────────┘    └──────────────┘
```

#### 3.2.1 Chat UI (Frontend)

- **Purpose:** Web-based conversational interface for user interaction.
- **Technology Options:**

| Framework | Pros | Cons |
|-----------|------|------|
| **Streamlit** | Fastest to build, built-in chat components | Limited customization |
| **Gradio** | Easy chatbot UI, HuggingFace integration | Less flexible layout |
| **Flask + HTML/JS** | Full control over design | More development effort |
| **FastAPI + React** | Professional-grade, API-first | Heaviest to build |

- **Recommended:** `Streamlit` for v1 (rapid prototyping, built-in `st.chat_message` / `st.chat_input`).

- **UI Features:**
  - Chat message history (user + bot)
  - Source attribution links (back to Groww URLs)
  - Fund name auto-suggestions
  - Typing indicator / loading state
  - Disclaimer footer

#### 3.2.2 Query Encoder

- **Purpose:** Encode the user's natural-language query into the same embedding space as the stored chunks.
- **Technology:** Same embedding model used during ingestion (critical — must match).
- **Process:** `user_query → embedding_model → query_vector`

#### 3.2.3 Retriever

- **Purpose:** Find the top-K most relevant chunks from the vector store for the given query.
- **Strategy:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `top_k` | 3–5 | Enough context without overwhelming the LLM |
| `similarity_metric` | Cosine Similarity | Standard for text embeddings |
| `score_threshold` | 0.7 (optional) | Filter out low-relevance results |
| `metadata_filter` | Optional fund name filter | If user mentions a specific fund |

- **Retrieval Flow:**

```
User Query: "What is the expense ratio of HDFC Mid Cap Fund?"
       │
       ▼
 ┌─────────────┐
 │ Embed Query  │  ──▶  query_vector [0.12, -0.34, 0.56, ...]
 └─────────────┘
       │
       ▼
 ┌─────────────┐
 │ Vector Store │  ──▶  Top-K chunks by cosine similarity
 │ .query()     │       (with metadata: fund_name, source_url)
 └─────────────┘
       │
       ▼
 Retrieved Chunks:
   1. "HDFC Mid Cap Fund ... expense ratio 0.75% ..." (score: 0.94)
   2. "Fund details ... AUM ₹97,350 Cr ..."          (score: 0.87)
   3. "Mid Cap category ... Very High risk ..."       (score: 0.81)
```

#### 3.2.4 Prompt Builder

- **Purpose:** Construct the final LLM prompt by combining the system instruction, retrieved context, and user query.
- **Prompt Template:**

```
SYSTEM PROMPT:
You are an expert mutual fund assistant specializing in HDFC Mutual Fund schemes.
Answer the user's question ONLY based on the provided context from Groww.in data.
If the answer is not in the context, say "I don't have this information in my knowledge base."
Always mention the source fund name in your answer.
Do NOT provide financial advice or recommendations. Add a disclaimer when relevant.

CONTEXT:
{retrieved_chunks}

USER QUESTION:
{user_query}

INSTRUCTIONS:
- Be concise and accurate.
- Use bullet points or tables for structured data.
- Cite the fund name and data point source.
- If comparing funds, present data side by side.
```

#### 3.2.5 LLM (Answer Generator)

- **Purpose:** Generate a natural-language answer grounded in the retrieved context.
- **Provider:** **Groq** — ultra-fast LLM inference via their LPU (Language Processing Unit) hardware.

| Model | Provider | Speed | Quality | Free Tier |
|-------|----------|-------|---------|-----------|
| **`llama-3.1-8b-instant`** ✅ | Groq | ~500 tok/s | Good | Yes |
| `llama-3.1-70b-versatile` | Groq | ~300 tok/s | Excellent | Yes (rate-limited) |
| `mixtral-8x7b-32768` | Groq | ~400 tok/s | Very Good | Yes |
| `gemma2-9b-it` | Groq | ~450 tok/s | Good | Yes |

- **Selected:** `llama-3.1-8b-instant` via Groq API — fastest inference speed, free tier available, excellent for RAG-based Q&A.
- **Why Groq?** Groq's LPU delivers 10–20x faster inference than GPU-based providers, resulting in sub-second LLM response times. Combined with the ≤5s latency target, Groq ensures the online pipeline stays performant.

- **Parameters:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `temperature` | 0.1–0.3 | Low randomness for factual financial data |
| `max_tokens` | 500–1000 | Sufficient for detailed answers |
| `top_p` | 0.9 | Focused token selection |

#### 3.2.6 Response Formatter

- **Purpose:** Format the LLM's raw output for display in the chat UI.
- **Features:**
  - Markdown rendering (tables, bullet points, bold text)
  - Source attribution links (clickable Groww URLs)
  - Confidence indicator (based on retrieval similarity scores)
  - Disclaimer appending when discussing returns or risk

---

## 4. Data Flow Diagrams

### 4.1 Ingestion Flow (Offline)

```
  ┌─────────┐
  │  START  │
  └────┬────┘
       │
       ▼
  ┌──────────────────┐
  │ Load URL Config   │
  │ (5 Groww URLs)    │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐     ┌──────────────┐
  │ For each URL:     │     │ Rate Limiter  │
  │ Scrape page HTML  │◀───│ (1-2 sec      │
  │ via Selenium      │     │  between reqs) │
  └────────┬─────────┘     └──────────────┘
           │
           ▼
  ┌──────────────────┐
  │ Parse HTML with   │
  │ BeautifulSoup     │
  │ Extract:          │
  │  - Structured     │
  │    data (tables)  │
  │  - Unstructured   │
  │    text (paras)   │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Chunk text using  │
  │ RecursiveChar     │
  │ TextSplitter      │
  │ (800 chars,       │
  │  150 overlap)     │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Generate          │
  │ embeddings for    │
  │ each chunk        │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Store in          │
  │ ChromaDB with     │
  │ metadata:         │
  │  - fund_name      │
  │  - source_url     │
  │  - section        │
  │  - scraped_at     │
  └────────┬─────────┘
           │
           ▼
     ┌─────────┐
     │  DONE   │
     └─────────┘
```

### 4.2 Query Flow (Online)

```
  ┌──────────────────┐
  │ User types query  │
  │ in Chat UI        │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Encode query      │
  │ using same        │
  │ embedding model   │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Query ChromaDB    │
  │ for top-K=5       │
  │ similar chunks    │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Build prompt:     │
  │ system_prompt     │
  │ + context_chunks  │
  │ + user_query      │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Call LLM API      │
  │ (Gemini / GPT)    │
  │ temp=0.2          │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Format response   │
  │ + add source URLs │
  │ + disclaimer      │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Display in        │
  │ Chat UI           │
  └──────────────────┘
```

---

## 5. Project Structure

```
RAG-based Mutual Fund FAQ Chatbot/
│
├── DOCS/
│   ├── problemStatement.md         # Problem definition & fund details
│   └── Architecture.md             # This document
│
├── config/
│   ├── fund_urls.py                # The 5 Groww URLs (single source of truth)
│   ├── settings.py                 # App-wide settings (chunk size, top-k, etc.)
│   └── prompts.py                  # System prompt templates
│
├── scraper/
│   ├── __init__.py
│   └── groww_scraper.py            # Selenium/Playwright scraper for Groww pages
│
├── extractor/
│   ├── __init__.py
│   └── content_extractor.py        # HTML → structured text extraction
│
├── chunker/
│   ├── __init__.py
│   └── text_chunker.py             # Text splitting with metadata
│
├── embeddings/
│   ├── __init__.py
│   └── embedder.py                 # Embedding generation (OpenAI / HuggingFace)
│
├── vectorstore/
│   ├── __init__.py
│   └── store.py                    # ChromaDB / FAISS operations
│
├── retriever/
│   ├── __init__.py
│   └── retriever.py                # Similarity search + metadata filtering
│
├── llm/
│   ├── __init__.py
│   ├── prompt_builder.py           # Prompt construction from context + query
│   └── generator.py                # LLM API calls (Gemini / GPT)
│
├── app/
│   └── chatbot.py                  # Streamlit chat UI (main entry point)
│
├── pipeline/
│   ├── __init__.py
│   ├── ingest.py                   # Full ingestion pipeline orchestrator
│   └── query.py                    # Full query pipeline orchestrator
│
├── chroma_db/                      # Persistent ChromaDB storage (auto-created)
│
├── tests/
│   ├── test_scraper.py
│   ├── test_extractor.py
│   ├── test_chunker.py
│   ├── test_retriever.py
│   └── test_e2e.py                 # End-to-end query tests
│
├── requirements.txt                # Python dependencies
├── .env                            # API keys (GROQ_API_KEY)
├── .gitignore
└── README.md
```

---

## 6. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | Python | 3.10+ | Core application language |
| **Web Scraping** | Selenium / Playwright | Latest | Render JS-heavy Groww pages |
| **HTML Parsing** | BeautifulSoup4 | 4.12+ | Extract content from HTML |
| **Text Splitting** | LangChain | 0.2+ | RecursiveCharacterTextSplitter |
| **Embeddings** | `BAAI/bge-small-en-v1.5` (BGE) | Latest | Free, local, high-quality embeddings |
| **Vector Store** | ChromaDB | 0.4+ | Persistent vector storage |
| **LLM** | Groq (`llama-3.1-8b-instant`) | Latest | Ultra-fast answer generation via LPU |
| **LLM Framework** | LangChain | 0.2+ | Chain orchestration |
| **Frontend** | Streamlit | 1.30+ | Chat UI |
| **Environment** | python-dotenv | Latest | API key management |
| **Testing** | pytest | 8.0+ | Unit & integration tests |

### Dependencies (`requirements.txt`)

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

---

## 7. API & Interface Design

### 7.1 Internal Module Interfaces

```python
# ─── Scraper Interface ───
class GrowwScraper:
    def scrape(url: str) -> str                         # Returns raw HTML
    def scrape_all() -> dict[str, str]                  # URL → HTML mapping

# ─── Extractor Interface ───
class ContentExtractor:
    def extract(html: str, url: str) -> FundDocument    # Structured + raw text

# ─── Chunker Interface ───
class FundTextChunker:
    def chunk(text: str, metadata: dict) -> list[Chunk] # Text → chunks with metadata

# ─── Embedder Interface ───
class Embedder:
    def embed(texts: list[str]) -> list[list[float]]    # Texts → vectors
    def embed_query(query: str) -> list[float]          # Single query → vector

# ─── VectorStore Interface ───
class VectorStore:
    def add(chunks: list[Chunk], embeddings: list) -> None
    def query(query_vector: list, top_k: int) -> list[Result]
    def delete_collection() -> None                     # For re-ingestion

# ─── Retriever Interface ───
class Retriever:
    def retrieve(query: str, top_k: int = 5) -> list[RetrievedChunk]

# ─── LLM Interface ───
class LLMGenerator:
    def generate(prompt: str) -> str                    # Prompt → answer

# ─── Pipeline Orchestrators ───
class IngestionPipeline:
    def run() -> None                                   # Full scrape → store

class QueryPipeline:
    def run(user_query: str) -> ChatResponse            # Query → response
```

### 7.2 Data Models

```python
@dataclass
class FundDocument:
    fund_name: str
    category: str
    sub_category: str
    risk_level: str
    nav: float
    nav_date: str
    aum: str
    expense_ratio: float
    rating: str
    returns_1y: float
    returns_3y: float
    returns_5y: float
    raw_text: str
    source_url: str
    scraped_at: datetime

@dataclass
class Chunk:
    content: str
    metadata: dict   # {fund_name, source_url, section, scraped_at}

@dataclass
class RetrievedChunk:
    content: str
    metadata: dict
    similarity_score: float

@dataclass
class ChatResponse:
    answer: str
    source_urls: list[str]
    source_funds: list[str]
    confidence: float      # Average similarity score of retrieved chunks
```

---

## 8. Deployment Architecture

### 8.1 Local Development (v1)

```
┌──────────────────────────────────────────────┐
│              Local Machine                    │
│                                               │
│  ┌───────────┐    ┌───────────────────────┐  │
│  │ Streamlit  │    │  ChromaDB             │  │
│  │ App        │◀──▶│  (./chroma_db/)       │  │
│  │ (port 8501)│    │                       │  │
│  └───────────┘    └───────────────────────┘  │
│        │                                      │
│        ▼                                      │
│  ┌───────────┐                               │
│  │ LLM API   │  ──▶  Groq Cloud (LPU)       │
│  │ (HTTPS)   │                               │
│  └───────────┘                               │
│                                               │
└──────────────────────────────────────────────┘
         ▲
         │ HTTP (browser)
         │
    ┌─────────┐
    │  User   │
    │ Browser │
    │ :8501   │
    └─────────┘
```

### 8.2 Run Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Run ingestion pipeline (scrape Groww → build vector store)
python -m pipeline.ingest

# 4. Launch chatbot UI
streamlit run app/chatbot.py
```

---

## 9. Security & Configuration

### 9.1 Environment Variables

```env
# .env file
GROQ_API_KEY=your_groq_api_key_here          # For Groq LLM (required)

# Model Configuration
GROQ_MODEL=llama-3.1-8b-instant
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Pipeline Settings
CHUNK_SIZE=800
CHUNK_OVERLAP=150
TOP_K=5
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=800
```

### 9.2 Security Considerations

| Concern | Mitigation |
|---------|------------|
| API key exposure | Store in `.env`, add to `.gitignore`, never commit |
| Groww rate limiting | Add 1–2 second delay between scrape requests |
| LLM prompt injection | Sanitize user input, use system prompt guardrails |
| Stale data | Timestamp all chunks, log last scrape date |
| Financial misinformation | Always append disclaimer, never claim to give financial advice |

---

## 10. Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Ingestion time (5 URLs) | < 2 minutes | End-to-end scrape → store |
| Query latency (P95) | ≤ 5 seconds | User query → displayed answer |
| Retrieval accuracy (Hit@3) | ≥ 85% | Relevant chunk in top-3 results |
| Answer correctness | ≥ 90% | Human evaluation on test set |
| Vector store size | < 500 MB | For 5 funds with all data |
| Concurrent users | 1–5 (v1) | Streamlit local deployment |

---

## 11. Future Enhancements (v2+)

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| More fund URLs | Add more HDFC or other AMC funds to config | High |
| Scheduled re-scraping | Cron job to refresh data daily/weekly | High |
| Conversation memory | Multi-turn chat with context window | Medium |
| Reranking | Cross-encoder reranker for better retrieval | Medium |
| Hybrid search | Combine vector search with BM25 keyword search | Medium |
| Caching layer | Cache frequent queries and LLM responses | Medium |
| Cloud deployment | Deploy on Streamlit Cloud / GCP / AWS | Low |
| Multi-language | Hindi + regional language support | Low |
| Analytics dashboard | Track query patterns, popular funds | Low |

---

## 12. Architecture Decision Records (ADRs)

### ADR-001: Groww.in as Sole Data Source

- **Decision:** Use only Groww.in fund pages as the external data source.
- **Context:** Multiple sources (PDFs, AMFI, SEBI) were considered but add complexity in parsing and maintenance.
- **Rationale:** Groww pages contain all necessary fund data in a single, consistently structured format. Simplifies the ingestion pipeline.
- **Consequences:** Limited to data available on Groww; some deep regulatory details may be missing.

### ADR-002: ChromaDB over FAISS

- **Decision:** Use ChromaDB as the primary vector store.
- **Context:** FAISS is faster but lacks built-in persistence and metadata filtering.
- **Rationale:** ChromaDB offers persistent storage, metadata filtering (filter by fund name), and easy LangChain integration.
- **Consequences:** Slightly slower than FAISS for large datasets, but negligible for 5-fund corpus.

### ADR-003: Streamlit for UI

- **Decision:** Use Streamlit for the chat interface in v1.
- **Context:** React, Gradio, and Flask were considered.
- **Rationale:** Fastest to prototype, built-in chat components, single Python file, no frontend build step.
- **Consequences:** Limited UI customization; may migrate to React for v2 if needed.

### ADR-004: Selenium for Scraping

- **Decision:** Use Selenium (or Playwright) for web scraping.
- **Context:** `requests` + `BeautifulSoup` is lighter but cannot render JavaScript.
- **Rationale:** Groww.in is a Next.js app that renders most content via JavaScript; `requests` alone returns incomplete HTML.
- **Consequences:** Heavier dependency, requires browser driver, slower scraping.

---

> **Note:** This architecture is designed for v1 of the chatbot and is intentionally simple. Complexity should be added only when driven by real usage patterns and performance bottlenecks.
