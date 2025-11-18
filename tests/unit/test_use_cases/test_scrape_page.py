"""
Unit tests for ScrapePage use case.

End-to-end orchestration use case.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from scraper.use_cases.scrape_page import ScrapePage
from scraper.domain.models import (
    ExtractionResult,
    ExtractionMethod,
    PageType,
    PageTypeConfig,
    ScrapeResult,
)
from scraper.domain.exceptions import FetchError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_page_end_to_end():
    """GIVEN valid URL and config, WHEN scraping, THEN full workflow executes."""
    # Arrange
    fetcher = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    # Mock fetcher - include h1 so XPath extracts successfully
    fetcher.fetch = AsyncMock(return_value="<html><body><h1>John Doe</h1></body></html>")

    # Mock LLM (needed if any required fields are missing)
    llm.extract_fields = AsyncMock(return_value={})

    # Mock alerting
    alerting.send_alert = AsyncMock()

    # Mock storage - config exists
    config_dict = {
        "version": "1.0",
        "domain": "example.com",
        "page_type": "team_page",
        "selectors": {"name": {"xpath": "//h1"}},
        "schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    }
    storage.load_config = AsyncMock(return_value=config_dict)
    storage.save_html = AsyncMock(return_value="data/html/example.com/test.html")
    storage.save_json = AsyncMock(return_value="data/json/example.com/test.json")
    storage.update_coverage_stats = AsyncMock()
    storage.get_coverage_stats = AsyncMock(return_value={})

    use_case = ScrapePage(fetcher, llm, storage, alerting)

    # Act
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
    )

    # Assert
    assert result.success is True
    assert result.domain == "example.com"
    assert result.page_type == PageType.TEAM_PAGE
    fetcher.fetch.assert_called_once_with("https://example.com/team")
    storage.load_config.assert_called_once()
    storage.save_html.assert_called_once()
    storage.save_json.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_page_handles_fetch_error():
    """GIVEN URL that fails to fetch, WHEN scraping, THEN returns failed result."""
    fetcher = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    fetcher.fetch = AsyncMock(side_effect=FetchError("Connection timeout"))

    use_case = ScrapePage(fetcher, llm, storage, alerting)

    # Act
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
    )

    # Assert
    assert result.success is False
    assert result.extraction_method == ExtractionMethod.FAILED
    assert "Connection timeout" in result.error_message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_page_handles_missing_config():
    """GIVEN URL with no config, WHEN scraping, THEN returns failed result."""
    fetcher = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    fetcher.fetch = AsyncMock(return_value="<html>Test</html>")
    storage.load_config = AsyncMock(return_value=None)  # No config

    use_case = ScrapePage(fetcher, llm, storage, alerting)

    # Act
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
    )

    # Assert
    assert result.success is False
    assert "No config" in result.error_message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scrape_page_saves_html_and_json():
    """GIVEN successful extraction, WHEN scraping, THEN HTML and JSON are saved."""
    fetcher = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    fetcher.fetch = AsyncMock(return_value="<html>Test</html>")
    storage.load_config = AsyncMock(
        return_value={
            "version": "1.0",
            "domain": "example.com",
            "page_type": "team_page",
            "selectors": {"name": {"xpath": "//h1"}},
            "schema": {"type": "object", "properties": {}},
        }
    )
    storage.save_html = AsyncMock(return_value="/path/to/html")
    storage.save_json = AsyncMock(return_value="/path/to/json")
    storage.update_coverage_stats = AsyncMock()
    storage.get_coverage_stats = AsyncMock(return_value={})

    use_case = ScrapePage(fetcher, llm, storage, alerting)

    # Act
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
    )

    # Assert
    storage.save_html.assert_called_once()
    storage.save_json.assert_called_once()
    assert result.html_path == "/path/to/html"
    assert result.json_path == "/path/to/json"
