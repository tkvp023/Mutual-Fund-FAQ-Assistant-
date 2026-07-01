"""
Web scraper for Groww.in mutual fund pages.

Uses Selenium with headless Chrome to render JavaScript-heavy pages
(Groww is a Next.js app) and capture the fully-rendered HTML.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import json
from datetime import datetime


class GrowwScraper:
    """Scrapes Groww.in mutual fund pages using Selenium (headless Chrome)."""

    def __init__(self, urls: list[str], wait_time: int = 5, rate_limit: int = 2):
        """
        Args:
            urls: List of Groww.in mutual fund URLs to scrape.
            wait_time: Seconds to wait for JS rendering after page load.
            rate_limit: Seconds to wait between consecutive requests.
        """
        self.urls = urls
        self.wait_time = wait_time
        self.rate_limit = rate_limit

    def _get_driver(self) -> webdriver.Chrome:
        """Create and return a headless Chrome WebDriver instance."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        # Suppress logging noise
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        # Set a realistic user-agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def scrape(self, url: str) -> str:
        """
        Scrape a single Groww.in mutual fund page.

        Args:
            url: The Groww fund page URL.

        Returns:
            The fully-rendered HTML page source.

        Raises:
            Exception: If the page fails to load or render.
        """
        driver = self._get_driver()
        try:
            driver.get(url)

            # Wait for the main content to render (Groww loads fund data via JS)
            try:
                WebDriverWait(driver, self.wait_time + 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except Exception:
                # Fallback: just wait the configured time
                pass

            # Additional wait to ensure all dynamic content loads
            time.sleep(self.wait_time)

            return driver.page_source

        finally:
            driver.quit()

    def scrape_all(self) -> dict[str, str]:
        """
        Scrape all configured Groww fund URLs.

        Returns:
            Dictionary mapping URL → raw HTML page source.
        """
        results = {}
        total = len(self.urls)

        for i, url in enumerate(self.urls, 1):
            fund_slug = url.rstrip("/").split("/")[-1]
            print(f"  [{i}/{total}] Scraping: {fund_slug}")

            try:
                html = self.scrape(url)
                results[url] = html
                print(f"           [OK] Success - {len(html):,} chars of HTML")
            except Exception as e:
                print(f"           [FAIL] Failed - {str(e)}")
                results[url] = ""

            # Rate limiting between requests (skip after last URL)
            if i < total:
                print(f"           Waiting {self.rate_limit}s (rate limit)...")
                time.sleep(self.rate_limit)

        return results

    def save_raw_html(self, results: dict[str, str], output_dir: str = "data/raw_html") -> list[str]:
        """
        Save raw HTML results to disk for review/debugging.

        Args:
            results: Dictionary mapping URL → HTML content.
            output_dir: Directory to save HTML files.

        Returns:
            List of saved file paths.
        """
        os.makedirs(output_dir, exist_ok=True)
        saved_files = []

        for url, html in results.items():
            if not html:
                continue

            # Create filename from URL slug
            slug = url.rstrip("/").split("/")[-1]
            filepath = os.path.join(output_dir, f"{slug}.html")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)

            saved_files.append(filepath)
            print(f"  [SAVED] {filepath} ({len(html):,} chars)")

        # Save a metadata file with scrape info
        metadata = {
            "scraped_at": datetime.now().isoformat(),
            "total_urls": len(results),
            "successful": len(saved_files),
            "failed": len(results) - len(saved_files),
            "urls": list(results.keys()),
            "files": saved_files,
        }
        metadata_path = os.path.join(output_dir, "_scrape_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return saved_files
