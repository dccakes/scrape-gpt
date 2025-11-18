"""
Unit tests for LocalStorage adapter.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from scraper.adapters.storage.local_storage import LocalStorage


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorage(base_path=tmpdir)
        yield storage


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_and_load_config(temp_storage):
    """GIVEN config dict, WHEN saving and loading, THEN config is persisted."""
    config = {
        "version": "1.0",
        "domain": "example.com",
        "page_type": "team_page",
        "selectors": {"name": {"xpath": "//h1/text()"}},
    }

    # Save
    path = await temp_storage.save_config("example.com", "team_page", config)
    assert Path(path).exists()

    # Load
    loaded = await temp_storage.load_config("example.com", "team_page")
    assert loaded == config


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_nonexistent_config_returns_none(temp_storage):
    """GIVEN nonexistent config, WHEN loading, THEN returns None."""
    loaded = await temp_storage.load_config("nonexistent.com", "unknown_page")
    assert loaded is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_html(temp_storage):
    """GIVEN HTML content, WHEN saving, THEN file is created."""
    html = "<html><body>Test</body></html>"
    timestamp = datetime(2025, 1, 1, 12, 0, 0)

    path = await temp_storage.save_html(
        domain="example.com",
        url="https://example.com/page",
        html=html,
        timestamp=timestamp,
    )

    assert Path(path).exists()
    with open(path, "r") as f:
        assert f.read() == html


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_json(temp_storage):
    """GIVEN extracted data, WHEN saving, THEN JSON file is created."""
    data = {"name": "John Doe", "title": "CTO"}
    timestamp = datetime(2025, 1, 1, 12, 0, 0)

    path = await temp_storage.save_json(
        domain="example.com",
        url="https://example.com/page",
        data=data,
        timestamp=timestamp,
    )

    assert Path(path).exists()
    with open(path, "r") as f:
        loaded = json.load(f)
        assert loaded == data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_coverage_stats(temp_storage):
    """GIVEN field extractions, WHEN updating stats, THEN stats are tracked."""
    # Update stats multiple times
    await temp_storage.update_coverage_stats("example.com", "team_page", "name", True)
    await temp_storage.update_coverage_stats("example.com", "team_page", "name", True)
    await temp_storage.update_coverage_stats("example.com", "team_page", "name", False)
    await temp_storage.update_coverage_stats("example.com", "team_page", "email", True)

    # Get stats
    stats = await temp_storage.get_coverage_stats("example.com", "team_page")

    # name: 2 successes / 3 total = 0.667
    assert abs(stats["name"] - 0.667) < 0.01
    # email: 1 success / 1 total = 1.0
    assert stats["email"] == 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_coverage_stats_empty(temp_storage):
    """GIVEN no stats, WHEN getting stats, THEN returns empty dict."""
    stats = await temp_storage.get_coverage_stats("example.com", "team_page")
    assert stats == {}
