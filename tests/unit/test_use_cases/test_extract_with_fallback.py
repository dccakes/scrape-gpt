"""
Unit tests for ExtractWithFallback use case.

This is the key Phase 1 feature for field-level LLM fallback.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from scraper.use_cases.extract_with_fallback import ExtractWithFallback
from scraper.domain.models import (
    ExtractionResult,
    ExtractionMethod,
    PageType,
    PageTypeConfig,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_field_level_fallback_only_extracts_missing_fields():
    """GIVEN XPath extracted 9/10 fields, WHEN LLM fallback runs,
    THEN only the 1 missing field is sent to LLM."""
    # Arrange: Mock adapters
    extractor = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    # XPath extracts 9/10 fields (missing: email)
    xpath_result = ExtractionResult(
        data={"name": "John Doe", "title": "CTO", "phone": "555-1234"},
        extraction_method=ExtractionMethod.XPATH,
        confidence=0.9,
        fields_extracted=3,
        fields_missing=["email"],
        attempted_selectors={"name": "//h1", "title": "//div", "phone": "//span"},
    )
    extractor.extract.return_value = xpath_result

    # LLM extracts just the email
    llm.extract_fields = AsyncMock(return_value={"email": "john@example.com"})

    # Mock storage
    storage.update_coverage_stats = AsyncMock()
    storage.get_coverage_stats = AsyncMock(return_value={})

    # Mock config
    config = PageTypeConfig(
        version="1.0",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        selectors={
            "name": {"xpath": "//h1"},
            "title": {"xpath": "//div"},
            "phone": {"xpath": "//span"},
            "email": {"xpath": "//a"},
        },
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "title": {"type": "string"},
                "phone": {"type": "string"},
                "email": {"type": "string"},
            },
            "required": ["name", "email"],
        },
    )

    use_case = ExtractWithFallback(extractor, llm, storage, alerting)

    # Act: Execute extraction
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        html="<html>...</html>",
        config=config,
    )

    # Assert: Only missing field sent to LLM
    llm.extract_fields.assert_called_once()
    call_kwargs = llm.extract_fields.call_args[1]
    assert call_kwargs["fields_to_extract"] == ["email"]
    assert result.data["email"] == "john@example.com"
    assert result.llm_fields_used == ["email"]
    assert result.extraction_method == ExtractionMethod.XPATH_WITH_LLM_FALLBACK


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_fallback_when_all_fields_extracted():
    """GIVEN XPath extracted all fields, WHEN executing,
    THEN no LLM calls are made."""
    extractor = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    # XPath extracts all fields
    xpath_result = ExtractionResult(
        data={"name": "Jane Doe", "email": "jane@example.com"},
        extraction_method=ExtractionMethod.XPATH,
        confidence=1.0,
        fields_extracted=2,
        fields_missing=[],
    )
    extractor.extract.return_value = xpath_result

    storage.update_coverage_stats = AsyncMock()

    config = PageTypeConfig(
        version="1.0",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        selectors={"name": {"xpath": "//h1"}, "email": {"xpath": "//a"}},
        schema={
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "required": ["name", "email"],
        },
    )

    use_case = ExtractWithFallback(extractor, llm, storage, alerting)

    # Act
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        html="<html>...</html>",
        config=config,
    )

    # Assert: No LLM calls
    llm.extract_fields.assert_not_called()
    assert result.extraction_method == ExtractionMethod.XPATH
    assert result.llm_fields_used == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_updates_coverage_stats():
    """GIVEN extraction completes, WHEN use case runs,
    THEN coverage stats are updated for each field."""
    extractor = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    xpath_result = ExtractionResult(
        data={"name": "John Doe", "email": "john@example.com"},
        extraction_method=ExtractionMethod.XPATH,
        fields_extracted=2,
        fields_missing=[],
    )
    extractor.extract.return_value = xpath_result

    storage.update_coverage_stats = AsyncMock()
    storage.get_coverage_stats = AsyncMock(return_value={"name": 0.95, "email": 0.90})

    config = PageTypeConfig(
        version="1.0",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        selectors={"name": {"xpath": "//h1"}, "email": {"xpath": "//a"}},
        schema={"type": "object", "properties": {}},
    )

    use_case = ExtractWithFallback(extractor, llm, storage, alerting)

    # Act
    await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        html="<html>...</html>",
        config=config,
    )

    # Assert: Coverage stats updated
    assert storage.update_coverage_stats.call_count == 2
    # Note: get_coverage_stats is only called after LLM fallback path


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prefers_xpath_over_llm_values():
    """GIVEN both XPath and LLM extract same field, WHEN merging,
    THEN XPath value is preferred."""
    extractor = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    # XPath extracts name, missing email
    xpath_result = ExtractionResult(
        data={"name": "John from XPath"},
        extraction_method=ExtractionMethod.XPATH,
        fields_extracted=1,
        fields_missing=["email"],
    )
    extractor.extract.return_value = xpath_result

    # LLM returns both fields (but we only asked for email)
    llm.extract_fields = AsyncMock(
        return_value={"email": "john@example.com", "name": "John from LLM"}
    )

    storage.update_coverage_stats = AsyncMock()
    storage.get_coverage_stats = AsyncMock(return_value={})

    config = PageTypeConfig(
        version="1.0",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        selectors={"name": {"xpath": "//h1"}, "email": {"xpath": "//a"}},
        schema={
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "required": ["name", "email"],
        },
    )

    use_case = ExtractWithFallback(extractor, llm, storage, alerting)

    # Act
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        html="<html>...</html>",
        config=config,
    )

    # Assert: XPath value is preferred
    assert result.data["name"] == "John from XPath"
    assert result.data["email"] == "john@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handles_llm_failure_gracefully():
    """GIVEN LLM fails, WHEN fallback runs,
    THEN returns partial XPath results without crashing."""
    extractor = MagicMock()
    llm = MagicMock()
    storage = MagicMock()
    alerting = MagicMock()

    xpath_result = ExtractionResult(
        data={"name": "John Doe"},
        extraction_method=ExtractionMethod.XPATH,
        fields_extracted=1,
        fields_missing=["email"],
    )
    extractor.extract.return_value = xpath_result

    # LLM fails
    llm.extract_fields = AsyncMock(side_effect=Exception("API Error"))

    storage.update_coverage_stats = AsyncMock()
    storage.get_coverage_stats = AsyncMock(return_value={})
    alerting.send_alert = AsyncMock()

    config = PageTypeConfig(
        version="1.0",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        selectors={"name": {"xpath": "//h1"}, "email": {"xpath": "//a"}},
        schema={
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "required": ["name", "email"],
        },
    )

    use_case = ExtractWithFallback(extractor, llm, storage, alerting)

    # Act
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        html="<html>...</html>",
        config=config,
    )

    # Assert: Returns partial results
    assert result.data["name"] == "John Doe"
    assert "email" not in result.data or result.data["email"] is None
    # Alert should be sent
    alerting.send_alert.assert_called_once()
