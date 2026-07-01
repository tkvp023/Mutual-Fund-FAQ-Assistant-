"""
Preprocessors that transform raw extracted fund data into
clean, chunk-ready text strings for each section.
"""

import re
from datetime import datetime


def fmt_inr(value, suffix="Cr") -> str:
    """Format a float as an INR string. e.g. 97350.48 -> '₹97,350.48 Cr'"""
    if value is None:
        return "N/A"
    try:
        return f"₹{float(value):,.2f} {suffix}".strip()
    except (TypeError, ValueError):
        return str(value)


def fmt_pct(value) -> str:
    """Format a float as a percentage string. e.g. 21.62 -> '21.62%'"""
    if value is None:
        return "N/A"
    try:
        sign = "+" if float(value) >= 0 else ""
        return f"{sign}{float(value):.2f}%"
    except (TypeError, ValueError):
        return str(value)


# ─── Section synthesizers ────────────────────────────────────────────────────

def build_overview_chunk(doc: dict) -> str:
    """
    Synthesize a dense 'fund card' chunk from structured fields.
    This is the single most important chunk — answers most common queries.
    """
    lines = [
        f"Fund: {doc['fund_name']}",
        f"Category: {doc['category']} > {doc['sub_category']}",
        f"NAV: ₹{doc['nav']} (as of {doc['nav_date']})",
        f"AUM: {fmt_inr(doc['aum_cr'])}",
        f"Expense Ratio: {doc['expense_ratio']}%",
        f"Risk: {doc['stats'].get('risk', 'N/A')} (Rating: {doc.get('groww_rating', 'N/A')}/5)",
        f"Min SIP: ₹{doc['min_sip']} | Min Lumpsum: ₹{doc['min_lumpsum']}",
        f"Exit Load: {doc['exit_load']}",
        f"Stamp Duty: {doc['stamp_duty']}",
        f"Lock-in: {doc['lock_in']}",
        f"Benchmark: {doc['benchmark']}",
        f"Launch Date: {doc['launch_date']}",
        f"ISIN: {doc['isin']}",
    ]
    return "\n".join(l for l in lines if l and "N/A" not in l or "Risk" in l)


def build_about_chunk(doc: dict) -> str:
    """Build a narrative about-the-fund chunk."""
    lines = [
        f"About {doc['fund_name']}",
        f"{doc['description']}",
    ]
    # Add pros/cons if present
    analysis = doc.get("analysis", {})
    if analysis.get("pros"):
        lines.append("Strengths: " + "; ".join(analysis["pros"]))
    if analysis.get("cons"):
        lines.append("Weaknesses: " + "; ".join(analysis["cons"]))
    return "\n".join(lines)


def build_returns_chunk(doc: dict) -> str:
    """
    Build a structured returns chunk from cleaned return stats.
    Includes annualised returns, SIP XIRR, and category comparison.
    """
    ann = doc.get("returns_annualised", {})
    sip = doc.get("returns_sip", {})
    stats = doc.get("stats", {})

    rows = []
    periods = [("1m", "1M"), ("3m", "3M"), ("6m", "6M"), ("1y", "1Y"),
               ("3y", "3Y"), ("5y", "5Y"), ("10y", "10Y"), ("since_inception", "Since Inception")]

    for key, label in periods:
        ann_val = ann.get(key)
        sip_val = sip.get(key)
        if ann_val is not None or sip_val is not None:
            parts = [f"{label}:"]
            if ann_val is not None:
                parts.append(f"Annualised {fmt_pct(ann_val)}")
            if sip_val is not None:
                parts.append(f"SIP XIRR {fmt_pct(sip_val)}")
            rows.append("  " + " | ".join(parts))

    cat_lines = []
    if stats.get("cat_return_1y") is not None:
        cat_lines.append(f"Category avg 1Y: {fmt_pct(stats['cat_return_1y'])}")
    if stats.get("cat_return_3y") is not None:
        cat_lines.append(f"Category avg 3Y: {fmt_pct(stats['cat_return_3y'])}")
    if stats.get("cat_return_5y") is not None:
        cat_lines.append(f"Category avg 5Y: {fmt_pct(stats['cat_return_5y'])}")

    rank_lines = []
    for period, key in [("1Y", "rank_1y"), ("3Y", "rank_3y"), ("5Y", "rank_5y"), ("10Y", "rank_10y")]:
        r = stats.get(key)
        if r:
            rank_lines.append(f"Rank {period}: #{r} in {doc.get('sub_category', 'category')}")

    parts = [f"Returns for {doc['fund_name']}:"]
    parts += rows
    if cat_lines:
        parts.append("Vs Category:")
        parts += ["  " + c for c in cat_lines]
    if rank_lines:
        parts.append("Category Ranking:")
        parts += ["  " + r for r in rank_lines]

    return "\n".join(parts)


def build_exit_load_tax_chunk(doc: dict) -> str:
    """Build the exit load, stamp duty, and tax chunk."""
    lines = [
        f"Exit Load & Tax for {doc['fund_name']}",
        f"Exit Load: {doc['exit_load']}",
        f"Stamp Duty: {doc['stamp_duty']}",
        f"Lock-in Period: {doc['lock_in']}",
    ]
    # Add tax info from section text if available
    section_text = doc.get("sections", {}).get("exit_load_tax", "")
    if "LTCG" in section_text or "taxed" in section_text.lower():
        # Extract tax lines
        for line in section_text.split("\n"):
            if any(k in line.lower() for k in ["tax", "ltcg", "stcg", "redeem", "lakh"]):
                lines.append(line.strip())
    return "\n".join(l for l in lines if l.strip())


def build_investment_info_chunk(doc: dict) -> str:
    """Build the investment minimums chunk."""
    return (
        f"Investment Details for {doc['fund_name']}\n"
        f"Minimum SIP: ₹{doc['min_sip']}\n"
        f"Minimum Lumpsum: ₹{doc['min_lumpsum']}\n"
        f"Exit Load: {doc['exit_load']}\n"
        f"Lock-in: {doc['lock_in']}"
    )


def build_holdings_chunks(doc: dict, batch_size: int = 10) -> list:
    """
    Build holdings chunks grouped by sector, batched.
    Returns list of (text, metadata_extra) tuples.
    """
    holdings = doc.get("holdings", [])
    if not holdings:
        return []

    # Group by sector
    by_sector: dict = {}
    for h in holdings:
        sector = h.get("sector") or "Unspecified"
        by_sector.setdefault(sector, []).append(h)

    chunks = []
    portfolio_date = holdings[0].get("portfolio_date", "") if holdings else ""

    for sector, items in by_sector.items():
        # Batch within each sector
        for batch_start in range(0, len(items), batch_size):
            batch = items[batch_start: batch_start + batch_size]
            rows = []
            for h in batch:
                pct = f"{h['pct']:.2f}%" if h.get("pct") is not None else "N/A"
                rows.append(f"  {h['name']} ({h['instrument']}) — {pct}")

            text = (
                f"Portfolio Holdings for {doc['fund_name']} — {sector} Sector\n"
                f"(Portfolio date: {portfolio_date}, Total holdings: {len(holdings)})\n"
                + "\n".join(rows)
            )
            chunks.append((text, {"chunk_type": "holdings_batch", "holdings_sector": sector}))

    return chunks


def build_fund_management_chunks(doc: dict) -> list:
    """Build one chunk per fund manager (bio only, not the full funds-managed list)."""
    managers = doc.get("fund_managers", [])
    chunks = []
    for mgr in managers:
        text = (
            f"Fund Manager: {mgr['name']} — {doc['fund_name']}\n"
            f"Managing since: {mgr['since']}\n"
            f"Education: {mgr['education']}\n"
            f"Experience: {mgr['experience']}"
        )
        chunks.append((text, {"chunk_type": "fund_manager", "manager_name": mgr["name"]}))
    return chunks


def build_performance_ranking_chunk(doc: dict) -> str:
    """Build performance vs category and ranking chunk."""
    stats = doc.get("stats", {})
    ann = doc.get("returns_annualised", {})
    lines = [f"Performance & Rankings for {doc['fund_name']}"]

    # Fund returns vs category
    for period_key, period_label, cat_key in [
        ("1y", "1Y", "cat_return_1y"),
        ("3y", "3Y", "cat_return_3y"),
        ("5y", "5Y", "cat_return_5y"),
    ]:
        fund_ret = ann.get(period_key)
        cat_ret = stats.get(cat_key)
        if fund_ret is not None:
            line = f"  {period_label}: Fund {fmt_pct(fund_ret)}"
            if cat_ret is not None:
                line += f" | Category avg {fmt_pct(cat_ret)}"
            lines.append(line)

    # Rankings
    for period, key in [("1Y", "rank_1y"), ("3Y", "rank_3y"), ("5Y", "rank_5y"), ("10Y", "rank_10y")]:
        r = stats.get(key)
        if r:
            lines.append(f"  Rank {period}: #{r} in {doc.get('sub_category', 'category')}")

    # Risk metrics
    if stats.get("sharpe_ratio"):
        lines.append(f"Sharpe Ratio: {stats['sharpe_ratio']:.4f}")
    if stats.get("alpha"):
        lines.append(f"Alpha: {stats['alpha']:.4f}")
    if stats.get("beta"):
        lines.append(f"Beta: {stats['beta']:.4f}")

    return "\n".join(lines)


def build_peer_comparison_chunk(doc: dict) -> str:
    """Build a peer comparison chunk."""
    peers = doc.get("peers", [])
    if not peers:
        return ""

    rows = [f"Peer Comparison — {doc['fund_name']} vs Similar Funds ({doc['sub_category']})"]
    header = f"  {'Fund':<50} {'1Y':>8} {'3Y':>8} {'AUM(Cr)':>12}"
    rows.append(header)
    rows.append("  " + "-" * 80)

    for p in peers:
        name = (p.get("name") or "")[:48]
        r1y = fmt_pct(p.get("return_1y"))
        r3y = fmt_pct(p.get("return_3y"))
        aum = fmt_inr(p.get("aum_cr"), suffix="")
        rows.append(f"  {name:<50} {r1y:>8} {r3y:>8} {aum:>12}")

    return "\n".join(rows)


def build_fund_house_chunk(doc: dict) -> str:
    """Build a fund house chunk."""
    amc = doc.get("amc_info", {})
    if not amc:
        return ""
    lines = [
        f"Fund House: {amc.get('name', 'HDFC Mutual Fund')}",
        f"Total AUM: {fmt_inr(amc.get('aum_cr'))}",
        f"Website: {amc.get('website', '')}",
    ]
    if amc.get("phone"):
        lines.append(f"Phone: {amc['phone']}")
    if amc.get("email"):
        lines.append(f"Email: {amc['email']}")
    return "\n".join(l for l in lines if l.endswith(": ") is False)


def build_faq_chunks(doc: dict) -> list:
    """Build one chunk per FAQ Q&A pair."""
    chunks = []
    for qa in doc.get("faq", []):
        text = (
            f"Q: {qa['question']}\n"
            f"A: {qa['answer']}"
        )
        chunks.append((text, {"chunk_type": "faq"}))
    return chunks
