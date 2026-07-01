# RAG-based HDFC Mutual Fund FAQ Chatbot

An AI chatbot that answers questions about 5 HDFC Mutual Fund schemes using Retrieval-Augmented Generation (RAG).

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Embeddings** | BAAI/bge-small-en-v1.5 (BGE) |
| **Vector Store** | ChromaDB |
| **LLM** | Groq (llama-3.1-8b-instant) |
| **Frontend** | Streamlit |
| **Data Source** | Groww.in (5 fund URLs) |

## Covered Funds

1. HDFC Gold ETF Fund of Fund Direct Plan Growth
2. HDFC Large Cap Fund Direct Growth
3. HDFC Small Cap Fund Direct Growth
4. HDFC Silver ETF FoF Direct Growth
5. HDFC Mid Cap Fund Direct Growth

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd RAG-based-Mutual-Fund-FAQ-Chatbot

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 5. Run ingestion pipeline (scrape Groww → embed → store)
python -m pipeline.ingest

# 6. Launch chatbot UI
streamlit run app/chatbot.py
```

## Project Structure

```
├── DOCS/                  # Documentation
├── config/                # Configuration (URLs, settings, prompts)
├── scraper/               # Groww.in web scraper
├── extractor/             # HTML → text extraction
├── chunker/               # Text splitting
├── embeddings/            # BGE embedding generation
├── vectorstore/           # ChromaDB operations
├── retriever/             # Similarity search
├── llm/                   # Groq LLM integration
├── pipeline/              # Ingestion & query orchestrators
├── app/                   # Streamlit chat UI
├── tests/                 # Unit & integration tests
├── requirements.txt       # Python dependencies
├── .env                   # API keys (not committed)
└── .env.example           # Template for .env
```

## Documentation

- [Problem Statement](DOCS/problemStatement.md)
- [Architecture](DOCS/Architecture.md)
- [Implementation Plan](DOCS/implementation_plan.md)
- [Evaluation Plan](DOCS/eval.md)

## Disclaimer

This chatbot is for informational purposes only and does not constitute financial advice. Users should consult a certified financial advisor before making investment decisions.
