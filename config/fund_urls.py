"""
URL configuration for the RAG-based Mutual Fund FAQ Chatbot.

These are the 5 Groww.in fund page URLs that serve as the
sole external data source for the chatbot's knowledge base.
"""

FUND_URLS = [
    "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
]

# Human-readable fund name mapping (URL slug → display name)
FUND_NAMES = {
    "hdfc-gold-etf-fund-of-fund-direct-plan-growth": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "hdfc-large-cap-fund-direct-growth": "HDFC Large Cap Fund Direct Growth",
    "hdfc-small-cap-fund-direct-growth": "HDFC Small Cap Fund Direct Growth",
    "hdfc-silver-etf-fof-direct-growth": "HDFC Silver ETF FoF Direct Growth",
    "hdfc-mid-cap-fund-direct-growth": "HDFC Mid Cap Fund Direct Growth",
}


def get_fund_name_from_url(url: str) -> str:
    """Extract the human-readable fund name from a Groww URL."""
    slug = url.rstrip("/").split("/")[-1]
    return FUND_NAMES.get(slug, slug)
