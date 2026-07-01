from pipeline.ingest import run_ingestion

# QueryPipeline is intentionally NOT imported here to avoid loading
# the LLM/Groq dependency when only running ingestion.
# Import it directly: from pipeline.query import QueryPipeline

__all__ = ["run_ingestion"]

