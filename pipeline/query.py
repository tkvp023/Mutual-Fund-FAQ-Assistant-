"""
Query Pipeline Orchestrator.

Connects the three-stage RAG pipeline:
  1. FundRetriever  — intent detection + filtered vector search
  2. build_prompt   — format system + user message with context
  3. GroqGenerator  — LLM answer generation

Usage:
    python -m pipeline.query
    python -m pipeline.query --query "What is the NAV of HDFC Mid Cap Fund?"
    python -m pipeline.query --debug    # show retrieved chunks + intent
"""

import os
import sys
import argparse

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from retriever.retriever import FundRetriever
from llm.prompt_builder import build_prompt, build_context_summary
from llm.generator import GroqGenerator


class QueryPipeline:
    """
    End-to-end RAG query pipeline.

    Initialises once and can answer multiple queries efficiently —
    the BGE model and ChromaDB client are loaded once at startup.
    """

    def __init__(self):
        print("  Initialising QueryPipeline...")
        self.retriever = FundRetriever()
        self.generator = GroqGenerator()
        print("  QueryPipeline ready.\n")

    def run(self, query: str, debug: bool = False) -> dict:
        """
        Run the full RAG pipeline for a single query.

        Args:
            query: User's natural language question.
            debug: If True, include retrieved chunks and intent in the result.

        Returns:
            dict with:
              answer:          str   — the generated answer
              query:           str   — the original query
              source_funds:    list  — unique fund names in retrieved context
              source_sections: list  — unique section types retrieved
              num_chunks:      int   — number of chunks used
              context_summary: str   — one-line retrieval summary
              (debug only)
              retrieved_chunks: list — full retrieved chunk dicts
              intent:           dict — IntentDetector output
        """
        # ── Step 1: Retrieve ──────────────────────────────────────────────────
        if debug:
            retrieved, intent = self.retriever.retrieve(query, debug=True)
        else:
            retrieved = self.retriever.retrieve(query)
            intent    = None

        # ── Step 2: Build prompt ──────────────────────────────────────────────
        system_prompt, user_message = build_prompt(query, retrieved)

        # ── Step 3: Generate ──────────────────────────────────────────────────
        gen_result = self.generator.generate_with_metadata(system_prompt, user_message)

        # ── Step 4: Collect provenance ────────────────────────────────────────
        source_funds = list(dict.fromkeys(
            c["metadata"].get("fund_name", "") for c in retrieved
        ))
        source_sections = list(dict.fromkeys(
            c["metadata"].get("section", "") for c in retrieved
        ))
        source_urls = list(dict.fromkeys(
            c["metadata"].get("source_url", "") for c in retrieved
            if c["metadata"].get("source_url")
        ))

        result = {
            "query":           query,
            "answer":          gen_result["answer"],
            "source_funds":    source_funds,
            "source_sections": source_sections,
            "source_urls":     source_urls,
            "num_chunks":      len(retrieved),
            "context_summary": build_context_summary(retrieved),
            "model":           gen_result["model"],
            "input_tokens":    gen_result["input_tokens"],
            "output_tokens":   gen_result["output_tokens"],
        }

        if debug:
            result["retrieved_chunks"] = retrieved
            result["intent"]           = intent

        return result


# ── CLI entry point ───────────────────────────────────────────────────────────

_DEMO_QUERIES = [
    "What is the NAV of HDFC Mid Cap Fund?",
    "What are the 3Y and 5Y returns of HDFC Small Cap Fund?",
    "What is the expense ratio of HDFC Gold ETF Fund of Fund?",
    "Compare the exit load of HDFC Mid Cap vs HDFC Large Cap Fund.",
    "Who manages HDFC Small Cap Fund and what is their experience?",
]


def run_demo(pipeline: QueryPipeline, debug: bool = False):
    """Run a set of demo queries and print formatted output."""
    print("=" * 70)
    print("  QUERY PIPELINE — Demo Queries")
    print("=" * 70)

    for i, query in enumerate(_DEMO_QUERIES, 1):
        print(f"\n{'─' * 70}")
        print(f"  Query {i}: {query}")
        print(f"{'─' * 70}")

        result = pipeline.run(query, debug=debug)

        print(f"\n  ANSWER:\n{result['answer']}\n")
        print(f"  Context: {result['context_summary']}")
        print(f"  Tokens:  {result['input_tokens']} in / {result['output_tokens']} out")

        if debug and result.get("intent"):
            intent = result["intent"]
            print(f"\n  Intent:")
            print(f"    Detected funds:  {intent.get('detected_funds', [])}")
            print(f"    Section hints:   {intent.get('section_hints', [])}")
            print(f"    Is comparative:  {intent.get('is_comparative', False)}")
            print(f"    Top-K used:      {intent.get('top_k', '?')}")

            print(f"\n  Retrieved chunks:")
            for j, c in enumerate(result["retrieved_chunks"], 1):
                m = c["metadata"]
                print(f"    [{j}] {m.get('fund_name','?')[:30]} | {m.get('section','?')} | score={c['score']:.3f}")
                print(f"         '{c['content'][:70].replace(chr(10), ' ')}...'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HDFC Fund RAG Query Pipeline")
    parser.add_argument("--query", "-q", type=str, default=None,
                        help="Single query to run (default: run demo queries)")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="Show retrieved chunks and intent detection output")
    args = parser.parse_args()

    pipeline = QueryPipeline()

    if args.query:
        result = pipeline.run(args.query, debug=args.debug)
        print(f"\nQuery:  {result['query']}")
        print(f"Answer: {result['answer']}")
        print(f"\nContext: {result['context_summary']}")
        if args.debug and result.get("intent"):
            import json
            print("\nIntent:", json.dumps(result["intent"], indent=2))
            print("\nChunks retrieved:")
            for c in result["retrieved_chunks"]:
                m = c["metadata"]
                print(f"  [{m.get('section')}] {m.get('fund_name','?')[:30]} score={c['score']:.3f}")
    else:
        run_demo(pipeline, debug=args.debug)
