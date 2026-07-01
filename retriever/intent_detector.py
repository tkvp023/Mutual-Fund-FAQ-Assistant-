"""
Intent Detector — keyword-based query classifier for the retrieval pipeline.

Maps a user query to:
  - The most likely fund(s) being asked about
  - The most relevant section types to search
  - Whether the query is comparative (cross-fund)
  - The recommended top_k for that query type

No LLM call is made here — pure keyword matching for speed and determinism.
"""

# ── Fund aliases → canonical fund_name ───────────────────────────────────────
FUND_ALIASES = {
    "mid cap":    "HDFC Mid Cap Fund Direct Growth",
    "midcap":     "HDFC Mid Cap Fund Direct Growth",
    "mid-cap":    "HDFC Mid Cap Fund Direct Growth",
    "mid cap fund": "HDFC Mid Cap Fund Direct Growth",
    "large cap":  "HDFC Large Cap Fund Direct Growth",
    "largecap":   "HDFC Large Cap Fund Direct Growth",
    "large-cap":  "HDFC Large Cap Fund Direct Growth",
    "large cap fund": "HDFC Large Cap Fund Direct Growth",
    "small cap":  "HDFC Small Cap Fund Direct Growth",
    "smallcap":   "HDFC Small Cap Fund Direct Growth",
    "small-cap":  "HDFC Small Cap Fund Direct Growth",
    "small cap fund": "HDFC Small Cap Fund Direct Growth",
    "gold etf":   "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "gold fund":  "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "gold fof":   "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "gold":       "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "silver etf": "HDFC Silver ETF FoF Direct Growth",
    "silver fof": "HDFC Silver ETF FoF Direct Growth",
    "silver fund":"HDFC Silver ETF FoF Direct Growth",
    "silver":     "HDFC Silver ETF FoF Direct Growth",
}

# ── Section routing rules: keyword → ordered target sections ─────────────────
SECTION_ROUTING = {
    # Core metrics → overview (contains NAV, AUM, expense, SIP, benchmark, risk)
    "nav":                ["overview"],
    "net asset value":    ["overview"],
    "aum":                ["overview"],
    "asset under management": ["overview"],
    "expense ratio":      ["overview", "investment_info"],
    "expense":            ["overview"],
    "benchmark":          ["overview"],
    "isin":               ["overview"],
    "launch date":        ["overview"],
    "risk":               ["overview", "performance_ranking", "about_fund"],
    "groww rating":       ["overview"],

    # Investment minimums
    "minimum sip":        ["investment_info", "overview"],
    "min sip":            ["investment_info", "overview"],
    "sip amount":         ["investment_info", "overview"],
    "minimum investment": ["investment_info", "overview"],
    "min investment":     ["investment_info", "overview"],
    "lumpsum":            ["investment_info", "overview"],
    "minimum lumpsum":    ["investment_info", "overview"],

    # Returns
    "return":             ["returns", "performance_ranking"],
    "returns":            ["returns", "performance_ranking"],
    "cagr":               ["returns"],
    "xirr":               ["returns"],
    "sip return":         ["returns"],
    "annualised":         ["returns"],
    "1 year":             ["returns"],
    "3 year":             ["returns"],
    "5 year":             ["returns"],
    "10 year":            ["returns"],
    "since inception":    ["returns"],
    "performance":        ["returns", "performance_ranking"],
    "how has":            ["returns"],

    # Risk/stats
    "sharpe":             ["performance_ranking"],
    "sharpe ratio":       ["performance_ranking"],
    "alpha":              ["performance_ranking"],
    "beta":               ["performance_ranking"],
    "volatility":         ["performance_ranking"],
    "standard deviation": ["performance_ranking"],
    "sortino":            ["performance_ranking"],
    "rank":               ["performance_ranking", "returns"],
    "ranking":            ["performance_ranking", "returns"],

    # Tax / fees
    "exit load":          ["exit_load_tax"],
    "ltcg":               ["exit_load_tax"],
    "stcg":               ["exit_load_tax"],
    "tax":                ["exit_load_tax"],
    "capital gain":       ["exit_load_tax"],
    "stamp duty":         ["exit_load_tax"],
    "redeem":             ["exit_load_tax"],
    "redemption":         ["exit_load_tax"],
    "withdraw":           ["exit_load_tax"],
    "lock in":            ["exit_load_tax", "overview"],
    "lock-in":            ["exit_load_tax", "overview"],

    # Holdings / portfolio
    "holding":            ["holdings"],
    "holdings":           ["holdings"],
    "portfolio":          ["holdings"],
    "sector":             ["holdings"],
    "stock":              ["holdings"],
    "top stocks":         ["holdings"],
    "top holdings":       ["holdings"],
    "where does":         ["holdings"],
    "invests in":         ["holdings"],

    # Fund manager
    "manager":            ["fund_management"],
    "who manages":        ["fund_management"],
    "fund manager":       ["fund_management"],
    "managed by":         ["fund_management"],
    "portfolio manager":  ["fund_management"],

    # Cross-fund comparison
    "compare":            ["peer_comparison", "returns"],
    "comparison":         ["peer_comparison", "returns"],
    "vs":                 ["peer_comparison", "returns"],
    "versus":             ["peer_comparison", "returns"],
    "better":             ["peer_comparison", "returns", "about_fund"],
    "best":               ["peer_comparison", "returns"],
    "similar funds":      ["peer_comparison"],
    "peer":               ["peer_comparison"],

    # FAQ / procedural
    "how to invest":      ["faq"],
    "how do i invest":    ["faq"],
    "how can i invest":   ["faq"],
    "kyc":                ["faq"],
    "steps to":           ["faq"],
    "how to":             ["faq"],
    "process":            ["faq"],

    # Qualitative
    "good":               ["about_fund", "faq"],
    "should i invest":    ["about_fund", "faq"],
    "is it safe":         ["about_fund", "performance_ranking"],
    "recommend":          ["about_fund", "faq"],
    "long term":          ["about_fund", "returns"],
    "objective":          ["about_fund"],
    "goal":               ["about_fund"],
    "about":              ["about_fund"],
    "what kind":          ["about_fund"],

    # Fund house
    "hdfc amc":           ["fund_house"],
    "fund house":         ["fund_house"],
    "amc":                ["fund_house"],
}

# ── Keywords that signal a comparative / cross-fund query ────────────────────
_COMPARATIVE_KEYWORDS = [
    "compare", " vs ", " versus ", "all funds", "which fund",
    "best fund", "all hdfc", "both funds", "every fund",
]


class IntentDetector:
    """
    Keyword-based intent detector.

    Classifies a user query into:
      - detected_funds:  list of full fund_name strings found
      - fund_filter:     single fund_name if exactly one fund detected, else None
      - section_hints:   ordered list of best-match sections (up to 3)
      - is_comparative:  True if query spans multiple funds
      - top_k:           recommended chunk count for this query type
    """

    def detect(self, query: str) -> dict:
        q = query.lower()

        # ── 1. Fund detection ─────────────────────────────────────────────────
        detected_funds = []
        # Sort by length descending so "gold etf" matches before "gold"
        for alias in sorted(FUND_ALIASES, key=len, reverse=True):
            if alias in q:
                full_name = FUND_ALIASES[alias]
                if full_name not in detected_funds:
                    detected_funds.append(full_name)

        # ── 2. Section routing ────────────────────────────────────────────────
        section_scores: dict[str, int] = {}
        # Sort by keyword length descending (longer = more specific)
        for keyword in sorted(SECTION_ROUTING, key=len, reverse=True):
            if keyword in q:
                for i, sec in enumerate(SECTION_ROUTING[keyword]):
                    # Weight: first section gets 2 pts, second 1 pt
                    section_scores[sec] = section_scores.get(sec, 0) + max(2 - i, 1)

        ordered_sections = sorted(section_scores, key=section_scores.get, reverse=True)
        if not ordered_sections:
            ordered_sections = ["overview"]   # safe default

        # ── 3. Comparative detection ──────────────────────────────────────────
        is_comparative = (
            any(kw in q for kw in _COMPARATIVE_KEYWORDS)
            or len(detected_funds) > 1
        )

        # ── 4. Top-K decision ─────────────────────────────────────────────────
        if is_comparative:
            top_k = 5   # up to 1 chunk per fund
        elif ordered_sections and ordered_sections[0] in ("holdings",):
            top_k = 3   # sector-batched holdings
        elif ordered_sections and ordered_sections[0] in ("faq",):
            top_k = 3   # per-Q&A, get a few related
        else:
            top_k = 3   # single-fact: 1 exact + 2 context

        return {
            "detected_funds":  detected_funds,
            "fund_filter":     detected_funds[0] if len(detected_funds) == 1 else None,
            "section_hints":   ordered_sections[:3],
            "primary_section": ordered_sections[0] if ordered_sections else "overview",
            "is_comparative":  is_comparative,
            "top_k":           top_k,
        }
