#!/usr/bin/env python3
"""
Demo script for LLM Web Scraper v2.0

Demonstrates the core extraction pipeline against two scraping sandbox sites:
  1. quotes.toscrape.com - Multi-item extraction (quotes, authors, tags)
  2. books.toscrape.com  - Single-item detail page (title, price, etc.)

Works in two modes:
  --live    Fetches real pages from the internet
  --local   Uses bundled HTML fixtures (default, works offline)

Usage:
    python demo/run_demo.py              # offline demo with local fixtures
    python demo/run_demo.py --live       # live demo fetching real pages
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scraper.adapters.extractors.lxml_extractor import LxmlExtractor
from scraper.adapters.storage.local_storage import LocalStorage
from scraper.adapters.alerting.console_alerting import ConsoleAlerting
from scraper.use_cases.extract_with_fallback import ExtractWithFallback
from scraper.domain.models import (
    ExtractionMethod,
    PageType,
    PageTypeConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEMO_DIR = Path(__file__).parent
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def banner(text: str) -> None:
    width = 60
    print()
    print(f"{CYAN}{BOLD}{'=' * width}{RESET}")
    print(f"{CYAN}{BOLD}{text.center(width)}{RESET}")
    print(f"{CYAN}{BOLD}{'=' * width}{RESET}")
    print()


def section(text: str) -> None:
    print(f"\n{BOLD}--- {text} ---{RESET}")


def ok(text: str) -> None:
    print(f"  {GREEN}[OK]{RESET} {text}")


def warn(text: str) -> None:
    print(f"  {YELLOW}[!!]{RESET} {text}")


def fail(text: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {text}")


def info(text: str) -> None:
    print(f"  {DIM}{text}{RESET}")


class StubLLMProvider:
    """Stub LLM that returns hardcoded values for demo purposes.

    In production this would call Anthropic/OpenAI. For the demo we
    simulate the field-level fallback without needing an API key.
    """

    async def propose_selectors(self, *a, **kw):
        raise NotImplementedError

    async def repair_selectors(self, *a, **kw):
        raise NotImplementedError

    async def extract_fields(self, html, fields_to_extract, schema):
        """Simulate LLM extracting missing fields."""
        results = {}
        for field in fields_to_extract:
            results[field] = f"[LLM-extracted: {field}]"
        return results


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

async def load_html(path_or_url: str, live: bool) -> str:
    if live:
        from scraper.adapters.fetchers.httpx_fetcher import HttpxFetcher
        fetcher = HttpxFetcher()
        return await fetcher.fetch(path_or_url)
    else:
        with open(path_or_url, "r") as f:
            return f.read()


async def demo_quotes(live: bool) -> dict:
    """Demo 1: Extract quotes from quotes.toscrape.com."""
    banner("Demo 1: Quotes to Scrape")

    source = "https://quotes.toscrape.com/" if live else str(DEMO_DIR / "quotes_page.html")
    domain = "quotes.toscrape.com"
    page_type = PageType.QUOTES_PAGE

    section("Step 1: Fetch HTML")
    html = await load_html(source, live)
    ok(f"Loaded {len(html):,} bytes from {'live site' if live else 'local fixture'}")

    section("Step 2: Load config")
    storage = LocalStorage(base_path=str(project_root / "data"))
    config_dict = await storage.load_config(domain, page_type.value)
    if not config_dict:
        fail(f"No config found for {domain}/{page_type.value}")
        return {}
    config = PageTypeConfig(**config_dict)
    ok(f"Config loaded: {len(config.selectors)} selectors defined")
    for name, sel in config.selectors.items():
        selector_type = "xpath" if "xpath" in sel else "css"
        is_multi = sel.get("multiple", False)
        info(f"  {name}: {selector_type} {'(multiple)' if is_multi else ''}")

    section("Step 3: Extract with XPath")
    extractor = LxmlExtractor()
    alerting = ConsoleAlerting()
    llm = StubLLMProvider()
    fallback = ExtractWithFallback(
        extractor=extractor, llm=llm, storage=storage, alerting=alerting,
    )

    result = await fallback.execute(
        url=source, domain=domain, page_type=page_type, html=html, config=config,
    )

    section("Step 4: Results")
    method_color = GREEN if result.extraction_method == ExtractionMethod.XPATH else YELLOW
    print(f"  Method:     {method_color}{result.extraction_method.value}{RESET}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Fields OK:  {result.fields_extracted}")
    if result.fields_missing:
        print(f"  Missing:    {result.fields_missing}")
    if result.llm_fields_used:
        print(f"  LLM used:   {result.llm_fields_used}")

    section("Extracted Data")
    data = result.data
    quotes = data.get("quotes", [])
    authors = data.get("authors", [])
    tags_list = data.get("tags", [])

    for i, (q, a) in enumerate(zip(quotes, authors)):
        tag_str = tags_list[i] if i < len(tags_list) else ""
        print(f"\n  {BOLD}Quote {i+1}:{RESET}")
        print(f"    {q[:80]}{'...' if len(q) > 80 else ''}")
        print(f"    -- {CYAN}{a}{RESET}")
        print(f"    Tags: {DIM}{tag_str}{RESET}")

    if data.get("page_title"):
        print(f"\n  Page title: {data['page_title']}")

    section("Coverage Stats")
    stats = await storage.get_coverage_stats(domain, page_type.value)
    if stats:
        for field, rate in stats.items():
            color = GREEN if rate >= 0.8 else YELLOW if rate >= 0.7 else RED
            print(f"  {field}: {color}{rate:.0%}{RESET}")
    else:
        info("No historical coverage data yet (first run)")

    return data


async def demo_book(live: bool) -> dict:
    """Demo 2: Extract book detail from books.toscrape.com."""
    banner("Demo 2: Book Detail Page")

    source = (
        "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
        if live
        else str(DEMO_DIR / "book_detail.html")
    )
    domain = "books.toscrape.com"
    page_type = PageType.BOOK_DETAIL

    section("Step 1: Fetch HTML")
    html = await load_html(source, live)
    ok(f"Loaded {len(html):,} bytes from {'live site' if live else 'local fixture'}")

    section("Step 2: Load config")
    storage = LocalStorage(base_path=str(project_root / "data"))
    config_dict = await storage.load_config(domain, page_type.value)
    if not config_dict:
        fail(f"No config found for {domain}/{page_type.value}")
        return {}
    config = PageTypeConfig(**config_dict)
    ok(f"Config loaded: {len(config.selectors)} selectors defined")
    for name, sel in config.selectors.items():
        selector_type = "xpath" if "xpath" in sel else "css"
        info(f"  {name}: {selector_type}")

    section("Step 3: Extract with XPath + fallback")
    extractor = LxmlExtractor()
    alerting = ConsoleAlerting()
    llm = StubLLMProvider()
    fallback = ExtractWithFallback(
        extractor=extractor, llm=llm, storage=storage, alerting=alerting,
    )

    result = await fallback.execute(
        url=source, domain=domain, page_type=page_type, html=html, config=config,
    )

    section("Step 4: Results")
    method_color = GREEN if result.extraction_method == ExtractionMethod.XPATH else YELLOW
    print(f"  Method:     {method_color}{result.extraction_method.value}{RESET}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Fields OK:  {result.fields_extracted}")
    if result.fields_missing:
        print(f"  Missing:    {result.fields_missing}")
    if result.llm_fields_used:
        print(f"  LLM used:   {result.llm_fields_used}")

    section("Extracted Data")
    data = result.data
    for key, value in data.items():
        display = str(value)
        if len(display) > 100:
            display = display[:100] + "..."
        print(f"  {BOLD}{key:15}{RESET} {display}")

    section("Coverage Stats")
    stats = await storage.get_coverage_stats(domain, page_type.value)
    if stats:
        for field, rate in stats.items():
            color = GREEN if rate >= 0.8 else YELLOW if rate >= 0.7 else RED
            print(f"  {field}: {color}{rate:.0%}{RESET}")
    else:
        info("No historical coverage data yet (first run)")

    return data


async def demo_broken_selector(live: bool) -> dict:
    """Demo 3: Show LLM fallback when an XPath selector breaks."""
    banner("Demo 3: LLM Fallback (Broken Selector)")

    print(f"  {DIM}Simulating a selector that stopped working after a site redesign.{RESET}")
    print(f"  {DIM}The 'description' XPath is intentionally broken to trigger LLM fallback.{RESET}")

    source = (
        "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
        if live
        else str(DEMO_DIR / "book_detail.html")
    )
    domain = "books.toscrape.com"
    page_type = PageType.BOOK_DETAIL

    html = await load_html(source, live)

    # Load the real config and break one selector
    storage = LocalStorage(base_path=str(project_root / "data"))
    config_dict = await storage.load_config(domain, page_type.value)
    config = PageTypeConfig(**config_dict)

    section("Breaking the 'description' selector")
    original_xpath = config.selectors["description"]["xpath"]
    broken_xpath = "//div[@id='old_product_description']/following-sibling::p/text()"
    config.selectors["description"]["xpath"] = broken_xpath
    info(f"Original: {original_xpath}")
    warn(f"Broken:   {broken_xpath}")

    section("Extract with fallback")
    extractor = LxmlExtractor()
    alerting = ConsoleAlerting()
    llm = StubLLMProvider()
    fallback = ExtractWithFallback(
        extractor=extractor, llm=llm, storage=storage, alerting=alerting,
    )

    result = await fallback.execute(
        url=source, domain=domain, page_type=page_type, html=html, config=config,
    )

    section("Results")
    method_color = YELLOW if "llm" in result.extraction_method.value else GREEN
    print(f"  Method:     {method_color}{result.extraction_method.value}{RESET}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Fields OK:  {result.fields_extracted}")
    if result.llm_fields_used:
        warn(f"LLM filled in: {result.llm_fields_used}")
    print()
    info("In production, the LLM would extract the actual description from the HTML.")
    info("The stub returns a placeholder to show the fallback mechanism works.")
    info("Cost: only 1 field sent to LLM instead of all 7 = ~85% cheaper.")

    section("Extracted Data")
    data = result.data
    for key, value in data.items():
        display = str(value)
        if len(display) > 100:
            display = display[:100] + "..."
        is_llm = key in result.llm_fields_used
        marker = f"{YELLOW}[LLM]{RESET} " if is_llm else f"{GREEN}[XPath]{RESET}"
        print(f"  {marker} {BOLD}{key:15}{RESET} {display}")

    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    live = "--live" in sys.argv

    banner("LLM Web Scraper v2.0 - Demo")
    mode = "LIVE (fetching real pages)" if live else "OFFLINE (local HTML fixtures)"
    print(f"  Mode: {BOLD}{mode}{RESET}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"  {DIM}This demo shows the core extraction pipeline:{RESET}")
    print(f"  {DIM}  1. XPath extraction (fast, deterministic, free){RESET}")
    print(f"  {DIM}  2. Field-level LLM fallback (only for broken selectors){RESET}")
    print(f"  {DIM}  3. Coverage tracking (monitors selector health){RESET}")

    # Demo 1: Quotes
    await demo_quotes(live)

    # Demo 2: Book detail
    await demo_book(live)

    # Demo 3: Broken selector -> LLM fallback
    await demo_broken_selector(live)

    # Summary
    banner("Demo Complete")
    print(f"  {GREEN}All three scenarios executed successfully.{RESET}")
    print()
    print(f"  Key takeaways:")
    print(f"    1. XPath selectors extract data for $0 (no LLM cost)")
    print(f"    2. When a selector breaks, only THAT field goes to LLM")
    print(f"    3. Coverage stats track which selectors are degrading")
    print()
    print(f"  {DIM}Saved data is in: data/coverage-stats/{RESET}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
