"""
Integration tests for full extraction workflow.

Tests the actual adapters (no mocks) with test fixtures.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from scraper.adapters.extractors.lxml_extractor import LxmlExtractor
from scraper.adapters.storage.local_storage import LocalStorage
from scraper.adapters.alerting.console_alerting import ConsoleAlerting
from scraper.use_cases.extract_with_fallback import ExtractWithFallback
from scraper.domain.models import PageType, PageTypeConfig, ExtractionMethod


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def test_html():
    """Load test HTML fixture."""
    html_path = FIXTURES_DIR / "test_team_page.html"
    with open(html_path, "r") as f:
        return f.read()


@pytest.fixture
def test_config():
    """Load test config."""
    return PageTypeConfig(
        version="1.0",
        domain="test.local",
        page_type=PageType.TEAM_PAGE,
        selectors={
            "name": {"xpath": "//h1[@class='name']/text()"},
            "title": {"xpath": "//div[@class='title']/text()"},
            "email": {"xpath": "//a[contains(@href, 'mailto:')]/text()"},
            "phone": {"xpath": "//span[@class='phone']/text()"},
        },
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "title": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
            },
            "required": ["name", "email"],
        },
    )


@pytest.fixture
def temp_storage():
    """Create temporary storage for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalStorage(base_path=tmpdir)


class MockLLMProvider:
    """Mock LLM provider that returns empty dict (no fallback needed)."""

    async def extract_fields(self, html, fields_to_extract, schema):
        return {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lxml_extractor_extracts_from_test_html(test_html, test_config):
    """GIVEN test HTML and config, WHEN extracting with LxmlExtractor,
    THEN all fields are extracted correctly."""
    extractor = LxmlExtractor()

    result = extractor.extract(test_html, test_config.model_dump())

    # Should extract first team member
    assert result.data["name"] == "John Doe"
    assert result.data["title"] == "Chief Technology Officer"
    assert result.data["email"] == "john@testcompany.com"
    assert result.data["phone"] == "555-123-4567"
    assert result.extraction_method == ExtractionMethod.XPATH
    assert result.fields_extracted == 4
    assert len(result.fields_missing) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_with_fallback_full_xpath_success(
    test_html, test_config, temp_storage
):
    """GIVEN test HTML with all fields extractable,
    WHEN running ExtractWithFallback, THEN no LLM is called."""
    extractor = LxmlExtractor()
    llm = MockLLMProvider()
    alerting = ConsoleAlerting()

    use_case = ExtractWithFallback(
        extractor=extractor,
        llm=llm,
        storage=temp_storage,
        alerting=alerting,
    )

    result = await use_case.execute(
        url="https://test.local/team",
        domain="test.local",
        page_type=PageType.TEAM_PAGE,
        html=test_html,
        config=test_config,
    )

    # All fields extracted via XPath
    assert result.data["name"] == "John Doe"
    assert result.data["email"] == "john@testcompany.com"
    assert result.extraction_method == ExtractionMethod.XPATH
    assert result.llm_fields_used == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_storage_saves_and_loads_config(temp_storage):
    """GIVEN LocalStorage, WHEN saving and loading config,
    THEN config is persisted correctly."""
    config = {
        "version": "1.0",
        "domain": "test.local",
        "page_type": "team_page",
        "selectors": {"name": {"xpath": "//h1"}},
    }

    # Save
    path = await temp_storage.save_config("test.local", "team_page", config)
    assert Path(path).exists()

    # Load
    loaded = await temp_storage.load_config("test.local", "team_page")
    assert loaded == config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_storage_saves_html_and_json(temp_storage, test_html):
    """GIVEN LocalStorage, WHEN saving HTML and JSON,
    THEN files are created with correct content."""
    timestamp = datetime.now()
    data = {"name": "John Doe", "email": "john@test.com"}

    # Save HTML
    html_path = await temp_storage.save_html(
        domain="test.local",
        url="https://test.local/team",
        html=test_html,
        timestamp=timestamp,
    )
    assert Path(html_path).exists()
    with open(html_path) as f:
        assert "John Doe" in f.read()

    # Save JSON
    json_path = await temp_storage.save_json(
        domain="test.local",
        url="https://test.local/team",
        data=data,
        timestamp=timestamp,
    )
    assert Path(json_path).exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coverage_stats_tracking(temp_storage):
    """GIVEN LocalStorage, WHEN updating coverage stats,
    THEN stats are tracked correctly."""
    # Update stats
    await temp_storage.update_coverage_stats("test.local", "team_page", "name", True)
    await temp_storage.update_coverage_stats("test.local", "team_page", "name", True)
    await temp_storage.update_coverage_stats("test.local", "team_page", "name", False)

    # Get stats
    stats = await temp_storage.get_coverage_stats("test.local", "team_page")

    # 2/3 success = 66.7%
    assert abs(stats["name"] - 0.667) < 0.01


@pytest.mark.integration
def test_extractor_handles_css_selectors(test_html):
    """GIVEN HTML and CSS selectors, WHEN extracting,
    THEN CSS selectors work correctly."""
    extractor = LxmlExtractor()

    config = {
        "selectors": {
            "name": {"css": "h1.name"},
            "title": {"css": "div.title"},
        }
    }

    result = extractor.extract(test_html, config)

    assert result.data["name"] == "John Doe"
    assert result.data["title"] == "Chief Technology Officer"
