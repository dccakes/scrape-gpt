"""
Integration tests for demo website extraction.

Tests that the hand-crafted configs correctly extract data from
the demo HTML fixtures (quotes.toscrape.com, books.toscrape.com).
"""

import pytest
from pathlib import Path

from scraper.adapters.extractors.lxml_extractor import LxmlExtractor
from scraper.adapters.storage.local_storage import LocalStorage
from scraper.domain.models import ExtractionMethod, PageType, PageTypeConfig

DEMO_DIR = Path(__file__).parent.parent.parent / "demo"
DATA_DIR = Path(__file__).parent.parent.parent / "data"


@pytest.fixture
def extractor():
    return LxmlExtractor()


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(base_path=str(DATA_DIR))


@pytest.mark.integration
def test_quotes_page_extraction(extractor, storage):
    """GIVEN quotes HTML fixture and config, WHEN extracting, THEN all fields populated."""
    html = (DEMO_DIR / "quotes_page.html").read_text()
    import asyncio
    config_dict = asyncio.get_event_loop().run_until_complete(
        storage.load_config("quotes.toscrape.com", "quotes_page")
    )
    assert config_dict is not None

    result = extractor.extract(html, config_dict)

    assert result.extraction_method == ExtractionMethod.XPATH
    assert result.confidence == 1.0
    assert len(result.fields_missing) == 0

    # Verify quotes extracted
    assert len(result.data["quotes"]) == 5
    assert "Albert Einstein" in result.data["authors"]
    assert "J.K. Rowling" in result.data["authors"]
    assert len(result.data["tags"]) == 5
    assert result.data["page_title"] == "Quotes to Scrape"


@pytest.mark.integration
def test_book_detail_extraction(extractor, storage):
    """GIVEN book detail HTML fixture and config, WHEN extracting, THEN all fields populated."""
    html = (DEMO_DIR / "book_detail.html").read_text()
    import asyncio
    config_dict = asyncio.get_event_loop().run_until_complete(
        storage.load_config("books.toscrape.com", "book_detail")
    )
    assert config_dict is not None

    result = extractor.extract(html, config_dict)

    assert result.extraction_method == ExtractionMethod.XPATH
    assert result.confidence == 1.0
    assert len(result.fields_missing) == 0

    assert result.data["title"] == "A Light in the Attic"
    assert "51.77" in result.data["price"]
    assert "In stock" in result.data["availability"]
    assert "Three" in result.data["rating"]
    assert result.data["upc"] == "a897fe39b1053632"
    assert "Shel Silverstein" in result.data["description"]
    assert result.data["num_reviews"] == "0"


@pytest.mark.integration
def test_book_detail_broken_selector_triggers_missing_field(extractor, storage):
    """GIVEN a broken selector, WHEN extracting, THEN that field is in fields_missing."""
    html = (DEMO_DIR / "book_detail.html").read_text()
    import asyncio
    config_dict = asyncio.get_event_loop().run_until_complete(
        storage.load_config("books.toscrape.com", "book_detail")
    )

    # Break the description selector
    config_dict["selectors"]["description"]["xpath"] = (
        "//div[@id='old_product_description']/following-sibling::p/text()"
    )

    result = extractor.extract(html, config_dict)

    assert "description" in result.fields_missing
    assert result.fields_extracted == 6  # 7 total - 1 broken
    assert result.confidence < 1.0
