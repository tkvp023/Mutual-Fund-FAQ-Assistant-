"""
Phase 1 Runner -- Scrape & Extract (Steps 1.5 + 1.6)

This script:
  1. Scrapes all 5 Groww.in mutual fund pages (Phase 1.5)
  2. Extracts structured + unstructured content from the HTML (Phase 1.6)
  3. Saves all data to the data/ directory for review

Output structure:
  data/
  +-- raw_html/               # Raw HTML from each fund page
  |   +-- hdfc-gold-etf-fund-of-fund-direct-plan-growth.html
  |   +-- hdfc-large-cap-fund-direct-growth.html
  |   +-- hdfc-small-cap-fund-direct-growth.html
  |   +-- hdfc-silver-etf-fof-direct-growth.html
  |   +-- hdfc-mid-cap-fund-direct-growth.html
  |   +-- _scrape_metadata.json
  +-- extracted/              # Extracted structured data (JSON) + raw text (TXT)
  |   +-- hdfc-gold-etf-fund-of-fund-direct-plan-growth.json
  |   +-- hdfc-large-cap-fund-direct-growth.json
  |   +-- hdfc-small-cap-fund-direct-growth.json
  |   +-- hdfc-silver-etf-fof-direct-growth.json
  |   +-- hdfc-mid-cap-fund-direct-growth.json
  |   +-- raw_text/           # Plain text versions for easy review
  |   |   +-- hdfc-gold-etf-*.txt
  |   |   +-- ...
  |   +-- _extraction_summary.json
  +-- phase1_report.json      # Overall Phase 1 summary report

Usage:
  python scripts/run_phase1.py
"""

import sys
import os
import io
import json
from datetime import datetime

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path so we can import our modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.fund_urls import FUND_URLS
from config.settings import SCRAPER_WAIT_TIME, SCRAPER_RATE_LIMIT
from scraper.groww_scraper import GrowwScraper
from extractor.content_extractor import ContentExtractor


def run_phase1():
    """Execute the full Phase 1 pipeline: Scrape + Extract + Save."""

    start_time = datetime.now()

    print("=" * 70)
    print("  PHASE 1: Web Scraping & Content Extraction")
    print("=" * 70)
    print(f"\n  Start time: {start_time.isoformat()}")
    print(f"  URLs to scrape: {len(FUND_URLS)}")
    print(f"  Wait time per page: {SCRAPER_WAIT_TIME}s")
    print(f"  Rate limit between requests: {SCRAPER_RATE_LIMIT}s")

    # --- Step 1.5: Web Scraping ---
    print("\n" + "-" * 70)
    print("  STEP 1.5: Scraping Groww.in fund pages")
    print("-" * 70 + "\n")

    scraper = GrowwScraper(
        urls=FUND_URLS,
        wait_time=SCRAPER_WAIT_TIME,
        rate_limit=SCRAPER_RATE_LIMIT,
    )

    raw_html = scraper.scrape_all()

    # Count successes
    successful_scrapes = sum(1 for html in raw_html.values() if html)
    failed_scrapes = len(raw_html) - successful_scrapes

    print(f"\n  Scraping Results: {successful_scrapes}/{len(FUND_URLS)} pages scraped successfully")
    if failed_scrapes > 0:
        print(f"  WARNING: {failed_scrapes} page(s) failed to scrape")

    # Save raw HTML
    print("\n  Saving raw HTML files...")
    html_files = scraper.save_raw_html(raw_html, output_dir="data/raw_html")

    # --- Step 1.6: Content Extraction ---
    print("\n" + "-" * 70)
    print("  STEP 1.6: Extracting content from HTML")
    print("-" * 70 + "\n")

    extractor = ContentExtractor()
    documents = extractor.extract_all(raw_html)

    # Save extracted data
    print("\n  Saving extracted data...")
    extracted_files = extractor.save_extracted_data(documents, output_dir="data/extracted")

    # --- Phase 1 Report ---
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    report = {
        "phase": "Phase 1: Web Scraping & Content Extraction",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": round(duration, 1),
        "scraping": {
            "total_urls": len(FUND_URLS),
            "successful": successful_scrapes,
            "failed": failed_scrapes,
            "html_files_saved": len(html_files),
        },
        "extraction": {
            "total_documents": len(documents),
            "documents": [
                {
                    "fund_name": doc["fund_name"],
                    "source_url": doc["source_url"],
                    "raw_text_length": doc["raw_text_length"],
                    "nav_data": doc["nav"],
                    "details_found": len(doc["details"]),
                    "returns_found": len(doc["returns"]),
                    "holdings_found": len(doc["holdings"]),
                    "faqs_found": len(doc["faq"]),
                }
                for doc in documents
            ],
        },
        "output_files": {
            "raw_html_dir": "data/raw_html/",
            "extracted_data_dir": "data/extracted/",
            "raw_text_dir": "data/extracted/raw_text/",
        },
    }

    # Save report
    os.makedirs("data", exist_ok=True)
    report_path = "data/phase1_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # --- Summary ---
    print("\n" + "=" * 70)
    print("  PHASE 1 COMPLETE!")
    print("=" * 70)
    print(f"\n  Duration: {duration:.1f} seconds")
    print(f"\n  Output files:")
    print(f"     Raw HTML:        data/raw_html/ ({len(html_files)} files)")
    print(f"     Extracted JSON:  data/extracted/ ({len(documents)} files)")
    print(f"     Raw text:        data/extracted/raw_text/ ({len(documents)} files)")
    print(f"     Phase 1 report:  {report_path}")
    print(f"\n  Document Summary:")
    for doc in documents:
        print(f"     * {doc['fund_name']}")
        print(f"       Text: {doc['raw_text_length']:,} chars | "
              f"Returns: {len(doc['returns'])} | "
              f"Holdings: {len(doc['holdings'])} | "
              f"FAQs: {len(doc['faq'])}")
    print()


if __name__ == "__main__":
    run_phase1()
