"""
Content extractor for Groww.in mutual fund page HTML.

Strategy: Primary source is the __NEXT_DATA__ JSON embedded in the page,
which contains all structured fund data from Groww's API.
BeautifulSoup is used for FAQ (JSON-LD) and the section-split raw text only.
"""

from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import re


class ContentExtractor:
    """
    Extracts structured and unstructured content from Groww fund page HTML.

    Primary extraction: __NEXT_DATA__ JSON (Next.js SSR payload)
    Secondary extraction: JSON-LD FAQPage schema
    Tertiary: Raw text split into named sections for the chunker
    """

    # Section boundary markers found in Groww page text (ordered by appearance)
    _SECTION_MARKERS = [
        ("nav_header",        None),                            # everything before first real content
        ("overview",          r"NAV:?\s*\d{1,2}\s+\w+|₹\d"),
        ("returns",           r"Return calculator|Historic returns"),
        ("holdings",          r"Holdings\s*\(\d+\)"),
        ("investment_info",   r"Minimum investments"),
        ("performance_ranking", r"Returns and rankings|Annualised returns"),
        ("exit_load_tax",     r"Exit [Ll]oad\s*$|Exit load, stamp duty"),
        ("peer_comparison",   r"Compare similar funds"),
        ("fund_management",   r"Fund management"),
        ("about_fund",        r"About HDFC"),
        ("fund_house",        r"Fund house"),
        ("faq_section",       r"FAQs$|^FAQs"),
        ("footer",            r"Looking to invest|© 2016"),
    ]

    def extract(self, html: str, url: str) -> dict:
        """
        Extract all fund data from a Groww.in page HTML.

        Returns a dict with:
          - All structured fields from __NEXT_DATA__ (nav, aum, returns, holdings, etc.)
          - FAQ list from JSON-LD
          - Section-split raw text dict for the chunker
          - Raw full text for fallback
        """
        soup = BeautifulSoup(html, "html.parser")

        # ── Primary: __NEXT_DATA__ JSON ─────────────────────────────────────
        mf = self._extract_next_data(soup)

        # ── Secondary: FAQ from JSON-LD ──────────────────────────────────────
        faq = self._extract_faq_jsonld(soup)

        # ── Tertiary: section-split raw text ─────────────────────────────────
        raw_text = self._extract_clean_text(soup)
        sections = self._split_into_sections(raw_text)

        # ── Compose final document ────────────────────────────────────────────
        fund_name = mf.get("scheme_name") or self._extract_h1(soup)

        return {
            # identity
            "fund_name":        fund_name,
            "fund_slug":        url.rstrip("/").split("/")[-1],
            "source_url":       url,
            "scraped_at":       datetime.now().isoformat(),
            "isin":             mf.get("isin", ""),
            "scheme_code":      str(mf.get("scheme_code", "")),

            # key metrics (from __NEXT_DATA__)
            "nav":              mf.get("nav"),          # float e.g. 226.915
            "nav_date":         mf.get("nav_date", ""),
            "aum_cr":           mf.get("aum"),          # float crores
            "expense_ratio":    mf.get("expense_ratio", ""),  # e.g. "0.75"
            "category":         mf.get("category", ""),
            "sub_category":     mf.get("sub_category", ""),
            "benchmark":        mf.get("benchmark_name", ""),
            "groww_rating":     mf.get("groww_rating"),
            "risk":             "",                     # filled from return_stats below
            "launch_date":      mf.get("launch_date", ""),

            # investment details
            "min_lumpsum":      mf.get("min_investment_amount"),
            "min_sip":          mf.get("min_sip_investment"),
            "exit_load":        mf.get("exit_load", ""),
            "stamp_duty":       mf.get("stamp_duty", ""),
            "lock_in":          self._parse_lock_in(mf.get("lock_in", {})),

            # fund description / objective
            "description":      mf.get("description", ""),

            # returns — annualised %
            "returns_annualised": self._parse_returns(mf.get("return_stats")),

            # SIP returns
            "returns_sip":      self._parse_returns(mf.get("sip_return")),

            # risk/stats
            "stats":            self._parse_stats(mf.get("return_stats")),

            # holdings list
            "holdings":         self._parse_holdings(mf.get("holdings", [])),

            # fund managers
            "fund_managers":    self._parse_managers(mf.get("fund_manager_details", [])),

            # peer comparison
            "peers":            self._parse_peers(mf.get("peerComparison", [])),

            # pros/cons analysis
            "analysis":         self._parse_analysis(mf.get("analysis", [])),

            # FAQ (from JSON-LD — clean, no whitespace artifacts)
            "faq":              faq,

            # AMC info
            "amc_info":         self._parse_amc(mf.get("amc_info", {})),

            # section-split raw text (for chunker)
            "sections":         sections,

            # flat raw text (fallback)
            "raw_text":         raw_text,
            "raw_text_length":  len(raw_text),
        }

    # ─── __NEXT_DATA__ helpers ───────────────────────────────────────────────

    def _extract_next_data(self, soup: BeautifulSoup) -> dict:
        """Extract the __NEXT_DATA__ JSON embedded by Next.js SSR."""
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return {}
        try:
            data = json.loads(script.string)
            return data["props"]["pageProps"]["mfServerSideData"]
        except (KeyError, json.JSONDecodeError):
            return {}

    def _parse_returns(self, return_data) -> dict:
        """Parse a return_stats or sip_return dict into clean named fields."""
        if not return_data:
            return {}
        if isinstance(return_data, list):
            return_data = return_data[0] if return_data else {}

        mapping = {
            "1d":  "return1d",
            "1w":  "return1w",
            "1m":  "return1m",
            "3m":  "return3m",
            "6m":  "return6m",
            "1y":  "return1y",
            "3y":  "return3y",
            "5y":  "return5y",
            "10y": "return10y",
            "since_inception": "return_since_created",
        }
        result = {}
        for label, key in mapping.items():
            val = return_data.get(key)
            if val is not None:
                result[label] = round(float(val), 2)
        return result

    def _parse_stats(self, return_data) -> dict:
        """Extract risk metrics from return_stats."""
        if not return_data:
            return {}
        if isinstance(return_data, list):
            return_data = return_data[0] if return_data else {}

        return {
            "risk":               return_data.get("risk", ""),
            "risk_rating":        return_data.get("risk_rating"),
            "sharpe_ratio":       return_data.get("sharpe_ratio"),
            "beta":               return_data.get("beta"),
            "alpha":              return_data.get("alpha"),
            "standard_deviation": return_data.get("standard_deviation"),
            "sortino_ratio":      return_data.get("sortino_ratio"),
            "mean_return":        return_data.get("mean_return"),
            # category comparison
            "cat_return_1y":      return_data.get("cat_return1y"),
            "cat_return_3y":      return_data.get("cat_return3y"),
            "cat_return_5y":      return_data.get("cat_return5y"),
            # ranks
            "rank_1y":            return_data.get("rank1yr"),
            "rank_3y":            return_data.get("rank3yr"),
            "rank_5y":            return_data.get("rank5yr"),
            "rank_10y":           return_data.get("rank10yr"),
        }

    def _parse_holdings(self, holdings: list) -> list:
        """Parse holdings into clean dicts."""
        result = []
        for h in holdings:
            result.append({
                "name":        h.get("company_name", ""),
                "sector":      h.get("sector_name", ""),
                "instrument":  h.get("instrument_name", ""),
                "type":        h.get("nature_name", ""),
                "pct":         h.get("corpus_per"),
                "portfolio_date": h.get("portfolio_date", "")[:10] if h.get("portfolio_date") else "",
            })
        return result

    def _parse_managers(self, managers: list) -> list:
        """Parse fund manager details."""
        result = []
        for mgr in managers:
            # Parse date_from into year
            date_from = mgr.get("date_from", "")
            since_year = ""
            if date_from:
                try:
                    since_year = date_from[:4]
                except Exception:
                    pass

            # Get managed funds names only (not full objects)
            funds_managed = []
            for f in mgr.get("funds_managed", []):
                name = f.get("scheme_name") or f.get("name", "")
                if name:
                    funds_managed.append(name)

            result.append({
                "name":          mgr.get("person_name", ""),
                "since":         since_year,
                "education":     mgr.get("education", ""),
                "experience":    mgr.get("experience", ""),
                "funds_managed": funds_managed,
            })
        return result

    def _parse_peers(self, peers: list) -> list:
        """Parse peer comparison funds."""
        result = []
        for p in peers:
            result.append({
                "name":      p.get("scheme_name", p.get("search_id", "")),
                "return_1y": p.get("return1y"),
                "return_3y": p.get("return3y"),
                "aum_cr":    p.get("aum"),
            })
        return result

    def _parse_analysis(self, analysis) -> dict:
        """Parse PROS/CONS analysis items."""
        if not analysis:
            return {"pros": [], "cons": []}
        pros, cons = [], []
        items = analysis if isinstance(analysis, list) else []
        for item in items:
            desc = item.get("analysis_desc", "")
            if item.get("analysis_type") == "PROS":
                pros.append(desc)
            elif item.get("analysis_type") == "CONS":
                cons.append(desc)
        return {"pros": pros, "cons": cons}

    def _parse_amc(self, amc_info) -> dict:
        """Parse AMC/fund house info."""
        if not amc_info:
            return {}
        if isinstance(amc_info, list):
            amc_info = amc_info[0] if amc_info else {}
        return {
            "name":    amc_info.get("amc_name", amc_info.get("fund_house", "")),
            "aum_cr":  amc_info.get("total_aum", amc_info.get("aum")),
            "website": amc_info.get("website", ""),
            "phone":   amc_info.get("phone", ""),
            "email":   amc_info.get("email", ""),
        }

    def _parse_lock_in(self, lock_in: dict) -> str:
        """Convert lock_in dict to human string."""
        if not lock_in:
            return "None"
        years = lock_in.get("years")
        months = lock_in.get("months")
        days = lock_in.get("days")
        parts = []
        if years:
            parts.append(f"{years} year{'s' if years > 1 else ''}")
        if months:
            parts.append(f"{months} month{'s' if months > 1 else ''}")
        if days:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        return ", ".join(parts) if parts else "None"

    # ─── FAQ from JSON-LD ────────────────────────────────────────────────────

    def _extract_faq_jsonld(self, soup: BeautifulSoup) -> list:
        """Extract FAQ Q&A pairs from the FAQPage JSON-LD schema."""
        faqs = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue
            if data.get("@type") == "FAQPage":
                for item in data.get("mainEntity", []):
                    q = item.get("name", "").strip()
                    a_data = item.get("acceptedAnswer", {})
                    a_raw = a_data.get("text", "") if isinstance(a_data, dict) else ""
                    # Strip HTML tags that appear in the JSON-LD answer text
                    a_clean = BeautifulSoup(a_raw, "html.parser").get_text(separator=" ", strip=True)
                    # Collapse extra whitespace
                    a_clean = re.sub(r"\s+", " ", a_clean).strip()
                    if q:
                        faqs.append({"question": q, "answer": a_clean})
        return faqs

    # ─── Raw text + section split ────────────────────────────────────────────

    def _extract_h1(self, soup: BeautifulSoup) -> str:
        el = soup.find("h1")
        return el.get_text(strip=True) if el else ""

    def _extract_clean_text(self, soup: BeautifulSoup) -> str:
        """
        Extract clean visible text, removing scripts/styles/nav/footer tags.
        """
        soup_copy = BeautifulSoup(str(soup), "html.parser")
        for tag in soup_copy(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()
        text = soup_copy.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if len(line.strip()) >= 2]
        return "\n".join(lines)

    def _split_into_sections(self, raw_text: str) -> dict:
        """
        Split the raw text into named sections based on known Groww page structure.
        Returns dict: { section_name: text_content }
        """
        lines = raw_text.split("\n")
        n = len(lines)

        # Find boundary indices for each known section
        boundaries = {}   # section_name -> start_line_index

        for sec_name, pattern in self._SECTION_MARKERS[1:]:  # skip nav_header
            if pattern is None:
                continue
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    if sec_name not in boundaries:  # take first match
                        boundaries[sec_name] = i
                    break

        # Sort by line index
        ordered = sorted(boundaries.items(), key=lambda x: x[1])

        sections = {}
        for idx, (sec_name, start_idx) in enumerate(ordered):
            end_idx = ordered[idx + 1][1] if idx + 1 < len(ordered) else n
            section_lines = lines[start_idx:end_idx]
            sections[sec_name] = "\n".join(section_lines).strip()

        # Capture everything before first identified section as nav_header (to discard)
        if ordered:
            first_start = ordered[0][1]
            sections["nav_header"] = "\n".join(lines[:first_start]).strip()

        return sections

    # ─── Batch extraction ────────────────────────────────────────────────────

    def extract_all(self, html_results: dict) -> list:
        """Extract content from multiple scraped HTML pages."""
        documents = []
        total = len(html_results)

        for i, (url, html) in enumerate(html_results.items(), 1):
            if not html:
                print(f"  [{i}/{total}] SKIP (empty HTML): {url}")
                continue

            slug = url.rstrip("/").split("/")[-1]
            print(f"  [{i}/{total}] Extracting: {slug}")

            doc = self.extract(html, url)
            documents.append(doc)

            print(f"           [OK] Fund:     {doc['fund_name']}")
            print(f"           [OK] NAV:      {doc['nav']} ({doc['nav_date']})")
            print(f"           [OK] AUM:      Rs. {doc['aum_cr']:,.2f} Cr" if doc['aum_cr'] else "           [OK] AUM: N/A")
            print(f"           [OK] Expense:  {doc['expense_ratio']}%")
            print(f"           [OK] Holdings: {len(doc['holdings'])} stocks")
            print(f"           [OK] Returns:  {list(doc['returns_annualised'].keys())}")
            print(f"           [OK] FAQs:     {len(doc['faq'])}")
            print(f"           [OK] Sections: {list(doc['sections'].keys())}")

        return documents

    def save_extracted_data(self, documents: list, output_dir: str = "data/extracted") -> list:
        """Save extracted data to JSON + text files."""
        os.makedirs(output_dir, exist_ok=True)
        saved_files = []

        for doc in documents:
            slug = doc["fund_slug"]
            filepath = os.path.join(output_dir, f"{slug}.json")

            # Save everything except heavy raw_text in the JSON summary
            summary = {k: v for k, v in doc.items() if k not in ("raw_text", "sections")}
            summary["raw_text_length"] = doc["raw_text_length"]
            summary["section_names"] = list(doc["sections"].keys())

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            saved_files.append(filepath)
            print(f"  [SAVED] {filepath}")

        # Save raw text files
        raw_text_dir = os.path.join(output_dir, "raw_text")
        os.makedirs(raw_text_dir, exist_ok=True)
        for doc in documents:
            slug = doc["fund_slug"]
            text_path = os.path.join(raw_text_dir, f"{slug}.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(f"Fund: {doc['fund_name']}\n")
                f.write(f"Source: {doc['source_url']}\n")
                f.write(f"Scraped: {doc['scraped_at']}\n")
                f.write("=" * 80 + "\n\n")
                f.write(doc["raw_text"])
            saved_files.append(text_path)
            print(f"  [SAVED] {text_path}")

        # Save sections as separate files for inspection
        sections_dir = os.path.join(output_dir, "sections")
        os.makedirs(sections_dir, exist_ok=True)
        for doc in documents:
            slug = doc["fund_slug"]
            sec_path = os.path.join(sections_dir, f"{slug}_sections.json")
            with open(sec_path, "w", encoding="utf-8") as f:
                json.dump(doc["sections"], f, indent=2, ensure_ascii=False)
            saved_files.append(sec_path)

        # Summary
        summary_path = os.path.join(output_dir, "_extraction_summary.json")
        summary = {
            "extraction_timestamp": datetime.now().isoformat(),
            "total_documents": len(documents),
            "documents_summary": [
                {
                    "fund_name":       doc["fund_name"],
                    "source_url":      doc["source_url"],
                    "nav":             doc["nav"],
                    "nav_date":        doc["nav_date"],
                    "aum_cr":          doc["aum_cr"],
                    "expense_ratio":   doc["expense_ratio"],
                    "holdings_count":  len(doc["holdings"]),
                    "faq_count":       len(doc["faq"]),
                    "returns":         doc["returns_annualised"],
                    "raw_text_length": doc["raw_text_length"],
                }
                for doc in documents
            ],
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n  Summary saved: {summary_path}")

        return saved_files
