# Problem Statement: RAG-based Mutual Fund FAQ Chatbot

## 1. Background

Mutual fund investors — both new and experienced — frequently have questions about fund types, SIP plans, NAV calculations, tax implications, risk categories, and regulatory guidelines. Currently, finding accurate answers requires navigating lengthy fund documents, AMFI/SEBI resources, or waiting for customer support responses, leading to delays and frustration.

## 2. Problem

There is no centralized, intelligent, and conversational system that can:

- Instantly answer investor queries about **specific HDFC mutual fund schemes** with **accurate, up-to-date** information.
- Ground its responses in **authoritative source documents** (fund factsheets, Groww data, AMFI FAQs, SEBI guidelines, scheme documents) rather than relying solely on a language model's parametric knowledge.
- Minimize **hallucination** — a common pitfall of standalone large language models when asked domain-specific financial questions.

## 3. Proposed Solution

Build a **Retrieval-Augmented Generation (RAG)** chatbot focused on **5 specific HDFC Mutual Fund schemes** that:

1. **Ingests** curated knowledge about the target funds (fund details, NAV history, returns, expense ratios, portfolio composition, risk profiles, FAQs).
2. **Embeds** the documents into a vector store for efficient semantic search.
3. **Retrieves** the most relevant document chunks in response to a user's natural-language question.
4. **Generates** a grounded, context-aware answer using a Large Language Model (LLM) augmented with the retrieved context.

---

## 4. Target Mutual Fund Schemes

The chatbot will cover the following **5 HDFC Mutual Fund Direct Plan Growth** schemes:

### 4.1 HDFC Gold ETF Fund of Fund Direct Plan Growth

| Attribute | Details |
|-----------|---------|
| **Category** | Commodities — Gold |
| **Risk Level** | High |
| **NAV** | ₹43.28 (as of 25 Jun '26) |
| **Fund Size (AUM)** | ₹12,121.18 Cr |
| **Expense Ratio** | 0.20% |
| **Rating** | 3★ |
| **3Y Annualised Return** | +32.05% |
| **Min SIP** | ₹100 |
| **Source** | [Groww - HDFC Gold ETF FoF](https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth) |

**SIP Return History (₹5,000/month):**

| Period | Invested | Value | Returns |
|--------|----------|-------|---------|
| 1 Year | ₹60,000 | ₹73,373 | +22.29% |
| 3 Years | ₹1,80,000 | ₹3,31,508 | +84.17% |

---

### 4.2 HDFC Large Cap Fund Direct Growth

| Attribute | Details |
|-----------|---------|
| **Category** | Equity — Large Cap |
| **Risk Level** | Very High |
| **NAV** | ₹1,217.44 (as of 25 Jun '26) |
| **Fund Size (AUM)** | ₹37,808.31 Cr |
| **Expense Ratio** | 1.04% |
| **Rating** | 4★ |
| **3Y Annualised Return** | +12.53% |
| **Min SIP** | ₹100 |
| **Source** | [Groww - HDFC Large Cap Fund](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |

**SIP Return History (₹5,000/month):**

| Period | Invested | Value | Returns |
|--------|----------|-------|---------|
| 1 Year | ₹60,000 | ₹59,821 | -0.30% |
| 3 Years | ₹1,80,000 | ₹1,93,183 | +7.32% |

---

### 4.3 HDFC Small Cap Fund Direct Growth

| Attribute | Details |
|-----------|---------|
| **Category** | Equity — Small Cap |
| **Risk Level** | Very High |
| **NAV** | ₹158.07 (as of 25 Jun '26) |
| **Fund Size (AUM)** | ₹38,809.48 Cr |
| **Expense Ratio** | 0.77% |
| **Rating** | 4★ |
| **3Y Annualised Return** | +15.51% |
| **Min SIP** | ₹100 |
| **Source** | [Groww - HDFC Small Cap Fund](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |

**SIP Return History (₹5,000/month):**

| Period | Invested | Value | Returns |
|--------|----------|-------|---------|
| 1 Year | ₹60,000 | ₹58,410 | -2.65% |
| 3 Years | ₹1,80,000 | ₹1,93,762 | +7.65% |

---

### 4.4 HDFC Silver ETF FoF Direct Growth

| Attribute | Details |
|-----------|---------|
| **Category** | Commodities — Silver |
| **Risk Level** | Very High |
| **NAV** | ₹35.65 (as of 25 Jun '26) |
| **Fund Size (AUM)** | ₹4,893.86 Cr |
| **Expense Ratio** | 0.22% |
| **Rating** | -- (Not Rated) |
| **3Y Annualised Return** | +44.44% |
| **Min SIP** | ₹100 |
| **Source** | [Groww - HDFC Silver ETF FoF](https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth) |

**SIP Return History (₹5,000/month):**

| Period | Invested | Value | Returns |
|--------|----------|-------|---------|
| 3 Months | ₹15,000 | ₹15,286 | +1.91% |
| 6 Months | ₹30,000 | ₹33,745 | +12.48% |

---

### 4.5 HDFC Mid Cap Fund Direct Growth

| Attribute | Details |
|-----------|---------|
| **Category** | Equity — Mid Cap |
| **Risk Level** | Very High |
| **NAV** | ₹226.92 (as of 25 Jun '26) |
| **Fund Size (AUM)** | ₹97,350.48 Cr |
| **Expense Ratio** | 0.75% |
| **Rating** | 5★ |
| **3Y Annualised Return** | +21.62% |
| **Min SIP** | ₹100 |
| **Source** | [Groww - HDFC Mid Cap Fund](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) |

**SIP Return History (₹5,000/month):**

| Period | Invested | Value | Returns |
|--------|----------|-------|---------|
| 1 Year | ₹60,000 | ₹62,438 | +4.06% |
| 3 Years | ₹1,80,000 | ₹2,16,712 | +20.40% |

---

## 5. Fund Portfolio Summary

| # | Fund Name | Category | Risk | AUM (Cr) | Expense Ratio | Rating | 3Y Return |
|---|-----------|----------|------|----------|---------------|--------|-----------|
| 1 | HDFC Gold ETF FoF | Commodities / Gold | High | ₹12,121 | 0.20% | 3★ | +32.05% |
| 2 | HDFC Large Cap Fund | Equity / Large Cap | Very High | ₹37,808 | 1.04% | 4★ | +12.53% |
| 3 | HDFC Small Cap Fund | Equity / Small Cap | Very High | ₹38,809 | 0.77% | 4★ | +15.51% |
| 4 | HDFC Silver ETF FoF | Commodities / Silver | Very High | ₹4,894 | 0.22% | -- | +44.44% |
| 5 | HDFC Mid Cap Fund | Equity / Mid Cap | Very High | ₹97,350 | 0.75% | 5★ | +21.62% |

**Total AUM Coverage:** ~₹1,90,983 Cr across 5 funds

**Asset Class Mix:**
- **Equity Funds (3):** Large Cap, Mid Cap, Small Cap — covering full market-cap spectrum
- **Commodity Funds (2):** Gold ETF FoF, Silver ETF FoF — precious metals exposure

---

## 6. Objectives

| # | Objective | Success Criteria |
|---|-----------|-----------------|
| 1 | Accurate, grounded answers | Responses cite or are traceable to source documents; hallucination rate < 5% on a test set. |
| 2 | Low-latency responses | End-to-end response time ≤ 5 seconds for typical queries. |
| 3 | Fund-specific coverage | Covers all 5 target HDFC fund schemes including NAV, returns, SIP info, risk profiles, expense ratios, and portfolio details. |
| 4 | User-friendly interface | Conversational chat UI that is intuitive for non-technical investors. |
| 5 | Extensible knowledge base | New fund documents can be added to the vector store without re-architecting the system. |

## 7. Scope

### In Scope

- Document ingestion pipeline (fund factsheets, Groww data, PDF / TXT / CSV parsing, chunking, embedding).
- Knowledge base covering the **5 specific HDFC fund schemes** listed above.
- Vector database for storing and retrieving embeddings (e.g., FAISS, ChromaDB, Pinecone).
- LLM integration for answer generation (e.g., OpenAI GPT, Google Gemini, open-source models).
- Web-based chat interface for user interaction.
- Source attribution — showing which document(s) informed the answer.
- Fund comparison queries (e.g., "Compare HDFC Mid Cap vs HDFC Small Cap returns").

### Out of Scope (for initial version)

- Real-time NAV / market data feeds.
- Personalized portfolio recommendations or financial advisory.
- Multi-language support (English only in v1).
- User authentication and account management.
- Funds outside the 5 listed HDFC schemes.

## 8. Target Users

- **Retail mutual fund investors** seeking quick answers about these specific HDFC fund features, processes, and performance.
- **Financial advisors / distributors** looking for a quick-reference tool during client conversations.
- **Customer support teams** at AMCs who need an internal knowledge assistant.

## 9. Key Technical Components

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌─────────────┐
│  Document    │───▶│  Chunking &  │───▶│  Vector Store │───▶│  Retriever  │
│  Ingestion   │    │  Embedding   │    │  (FAISS /     │    │             │
│  (Fund Data) │    │  Pipeline    │    │   ChromaDB)   │    │             │
└─────────────┘    └──────────────┘    └───────────────┘    └──────┬──────┘
                                                                   │
                                                                   ▼
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌─────────────┐
│  Chat UI    │◀───│  Response    │◀───│  LLM (GPT /   │◀───│  Prompt     │
│  (Web App)  │    │  Formatter   │    │   Gemini)     │    │  Builder    │
└─────────────┘    └──────────────┘    └───────────────┘    └─────────────┘
```

### Corpus Definition

The RAG knowledge base (corpus) is built from the following **primary** and **supplementary** data sources.

#### Primary Corpus — Groww Fund Pages (Web-Scraped)

These are the **5 authoritative URLs** that serve as the primary corpus for the chatbot. Data is scraped/ingested from these pages to build the vector store.

| # | Fund | Groww URL |
|---|------|-----------|
| 1 | HDFC Gold ETF Fund of Fund | https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth |
| 2 | HDFC Large Cap Fund | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 3 | HDFC Small Cap Fund | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 4 | HDFC Silver ETF FoF | https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth |
| 5 | HDFC Mid Cap Fund | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |

**Data extracted from each URL includes:**
- Fund name, category, sub-category, and risk level
- Latest NAV and NAV date
- Fund size (AUM)
- Expense ratio
- Groww rating (star rating)
- Annualised returns (1Y, 3Y, 5Y)
- SIP return calculator data (monthly SIP history)
- Fund manager information
- Portfolio / holding details
- Peer comparison data
- Exit load and tax implications

#### Supplementary Corpus

| Source | Content | Format | URL / Location |
|--------|---------|--------|----------------|
| HDFC MF Factsheets | Scheme info, fund manager details, investment objective | PDF | https://www.hdfcfund.com |
| AMFI India | Scheme codes, daily NAV data | CSV / API | https://www.amfiindia.com |
| SEBI Guidelines | Regulatory info, categorization norms | PDF / Web | https://www.sebi.gov.in |
| Fund KIMs | Key Information Memorandums | PDF | Published by HDFC AMC |

#### Corpus Ingestion Pipeline

```
Groww URLs (5)  ──┐
                  ├──▶  Web Scraper  ──▶  Text Extraction  ──▶  Chunking  ──▶  Embedding  ──▶  Vector Store
Supplementary  ───┘     (BeautifulSoup /   (Markdown /         (RecursiveChar     (OpenAI /       (FAISS /
PDFs / CSVs              Selenium)          Plain Text)         TextSplitter)       HuggingFace)    ChromaDB)
```

## 10. Sample Queries the Chatbot Should Handle

| # | Query Type | Example |
|---|-----------|---------|
| 1 | Fund Info | "What is the NAV of HDFC Mid Cap Fund?" |
| 2 | Returns | "What are the 3-year returns of HDFC Gold ETF FoF?" |
| 3 | Comparison | "Compare HDFC Large Cap vs HDFC Mid Cap Fund" |
| 4 | Risk | "Which of the 5 funds has the lowest risk?" |
| 5 | SIP | "What is the minimum SIP amount for HDFC Silver ETF FoF?" |
| 6 | Expense | "Which fund has the lowest expense ratio?" |
| 7 | Rating | "Which fund has the highest Groww rating?" |
| 8 | Portfolio | "What does HDFC Small Cap Fund invest in?" |
| 9 | Recommendation | "Which fund is best for long-term wealth creation?" |
| 10 | General | "What is the difference between Gold ETF FoF and Silver ETF FoF?" |

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucination on financial data | High — could mislead investors | RAG retrieval grounds answers; add confidence scores and disclaimers. |
| Stale knowledge base | Medium — outdated fund info | Periodic re-ingestion pipeline; timestamp documents. |
| Embedding quality issues | Medium — irrelevant retrievals | Experiment with chunk sizes, overlap, and embedding models; use reranking. |
| API cost overruns | Low–Medium | Use token budgets, caching, and consider open-source LLM alternatives. |
| Scope creep beyond 5 funds | Low | Clearly defined fund list; extensibility built in for future additions. |

## 12. Success Metrics

- **Retrieval Accuracy (Hit Rate @ k):** ≥ 85% of queries retrieve a relevant chunk in the top-3 results.
- **Answer Correctness:** ≥ 90% of answers judged as correct by domain experts on a curated test set.
- **User Satisfaction:** Average rating ≥ 4/5 from pilot user feedback.
- **Response Latency:** P95 response time ≤ 5 seconds.
- **Fund Coverage:** 100% of the 5 target funds addressable by the chatbot.

---

> **Disclaimer:** This chatbot is intended for informational purposes only and does not constitute financial advice. Users should consult a certified financial advisor before making investment decisions. Data sourced from [Groww](https://groww.in) as of June 2026.
