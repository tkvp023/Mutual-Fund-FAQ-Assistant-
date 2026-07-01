"""
Prompt builder for the RAG pipeline.

Constructs the final prompt sent to Groq from:
  - System instructions (grounding, rules, fund list)
  - Retrieved context chunks (with source attribution)
  - User query
"""

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a facts-only mutual fund FAQ assistant specializing in HDFC Mutual Fund schemes.
You answer questions about 5 specific HDFC funds based ONLY on the provided context from Groww.in data.

═══════════════════════════════════════════
SCOPE — FACTS ONLY (you MUST answer these):
═══════════════════════════════════════════
- Expense ratio of a scheme
- Exit load details
- Minimum SIP amount
- ELSS lock-in period
- Riskometer classification
- Benchmark index
- Process to download statements or capital gains reports
- NAV, AUM, returns data, fund manager, top holdings
- Any other purely factual detail found in the context

═══════════════════════════════════════════
RESPONSE FORMAT — STRICTLY FOLLOW ALL RULES:
═══════════════════════════════════════════
1. Answer ONLY using the provided context. Do NOT use outside knowledge.
2. If the answer is not in the context, say: "I don't have this information in my knowledge base."
3. Always mention the specific fund name in your answer.
4. Your answer MUST be a MAXIMUM of 3 sentences. Never exceed 3 sentences under any circumstances.
5. Your answer MUST include EXACTLY ONE citation link to the relevant Groww.in fund page from this list:
   • https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth
   • https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
   • https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
   • https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth
   • https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
   Format the link as: [Source](URL)
6. Every response MUST end with this footer on a new line:
   "Last updated from sources: {current_date}"
   Replace {current_date} with today's date in DD-MMM-YYYY format (e.g., 01-Jul-2026).
7. For numerical data (NAV, AUM, returns), always include the unit (₹, %, Cr).

═══════════════════════════════════════════
REFUSAL — NON-FACTUAL / ADVISORY QUERIES:
═══════════════════════════════════════════
You MUST REFUSE any question that asks for opinions, recommendations, comparisons of merit, or investment advice. Examples of queries to refuse:
- "Should I invest in this fund?"
- "Which fund is better?"
- "Is this a good fund for me?"
- "Recommend a fund for tax saving"
- "Will this fund give good returns?"

When refusing, follow this EXACT format:
1. Politely decline in 1-2 sentences, clearly stating you only provide factual information.
2. Include EXACTLY ONE educational link from these resources:
   • https://www.amfiindia.com/investor-corner/knowledge-center.html
   • https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=13
   Format the link as: [AMFI Investor Education](URL) or [SEBI Investor Education](URL)
3. End with the footer: "Last updated from sources: {current_date}"

Example refusal:
"I'm a facts-only assistant and cannot provide investment advice or fund recommendations. For guidance on investing, please visit [AMFI Investor Education](https://www.amfiindia.com/investor-corner/knowledge-center.html).

Last updated from sources: 01-Jul-2026"

The 5 funds you know about:
- HDFC Gold ETF Fund of Fund Direct Plan Growth
- HDFC Large Cap Fund Direct Growth
- HDFC Small Cap Fund Direct Growth
- HDFC Silver ETF FoF Direct Growth
- HDFC Mid Cap Fund Direct Growth"""


def build_prompt(query: str, retrieved_chunks: list[dict]) -> tuple[str, str]:
    """
    Build the system prompt and user message separately for ChatGroq.

    Args:
        query:            The user's question.
        retrieved_chunks: List of chunk dicts from FundRetriever.retrieve().
                          Each has: content, metadata (fund_name, section, ...), score.

    Returns:
        (system_prompt, user_message) — passed as separate messages to ChatGroq.
    """
    if not retrieved_chunks:
        context = "No relevant information found in the knowledge base."
    else:
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            meta     = chunk.get("metadata", {})
            fund     = meta.get("fund_name", "Unknown Fund")
            section  = meta.get("section", "")
            score    = chunk.get("score", 0.0)
            content  = chunk["content"].strip()

            context_parts.append(
                f"[{i}] Source: {fund} | Section: {section} | Relevance: {score:.2f}\n"
                f"{content}"
            )
        context = "\n\n---\n\n".join(context_parts)

    user_message = (
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {query}\n\n"
        f"ANSWER:"
    )
    return SYSTEM_PROMPT, user_message


def build_context_summary(retrieved_chunks: list[dict]) -> str:
    """
    Build a one-line summary of what was retrieved (for logging/UI display).
    e.g. "3 chunks from: HDFC Mid Cap (overview, returns, exit_load_tax)"
    """
    if not retrieved_chunks:
        return "No chunks retrieved"
    fund_sections: dict[str, list[str]] = {}
    for c in retrieved_chunks:
        meta    = c.get("metadata", {})
        fund    = meta.get("fund_name", "Unknown")[:25]
        section = meta.get("section", "")
        fund_sections.setdefault(fund, []).append(section)

    parts = []
    for fund, sections in fund_sections.items():
        parts.append(f"{fund} ({', '.join(sections)})")
    return f"{len(retrieved_chunks)} chunks from: {' | '.join(parts)}"
