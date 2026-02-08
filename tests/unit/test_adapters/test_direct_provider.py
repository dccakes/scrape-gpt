"""
Unit tests for DirectProvider (LLM) adapter.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from scraper.adapters.llm.direct_provider import DirectProvider
from scraper.domain.exceptions import LLMError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_fields_with_anthropic():
    """GIVEN HTML and field list, WHEN extracting with Anthropic, THEN fields are extracted."""
    html = "<html><body><div class='email'>test@example.com</div></body></html>"
    fields_to_extract = ["email"]
    schema = {
        "type": "object",
        "properties": {"email": {"type": "string"}},
    }

    with patch("anthropic.Anthropic") as mock_anthropic:
        # Mock the Anthropic API response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"email": "test@example.com"}')]
        mock_client.messages.create.return_value = mock_message

        # Create provider AFTER setting up mock
        provider = DirectProvider(api_key="test-key", provider="anthropic")
        result = await provider.extract_fields(html, fields_to_extract, schema)

        assert result == {"email": "test@example.com"}
        # Verify API was called
        mock_client.messages.create.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_fields_truncates_html():
    """GIVEN very long HTML, WHEN extracting, THEN HTML is truncated to 12000 chars."""
    html = "x" * 20000  # Very long HTML
    fields_to_extract = ["name"]
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"name": "Test"}')]
        mock_client.messages.create.return_value = mock_message

        # Create provider AFTER setting up mock
        provider = DirectProvider(api_key="test-key", provider="anthropic")
        await provider.extract_fields(html, fields_to_extract, schema)

        # Check that the HTML sent was truncated
        call_args = mock_client.messages.create.call_args
        messages = call_args[1]["messages"]
        content = messages[0]["content"]

        # HTML should be truncated in the prompt
        assert len(html) > 12000
        assert "..." in content or len(content) < 15000  # Truncation should happen


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_fields_raises_on_api_error():
    """GIVEN API error, WHEN extracting, THEN raises LLMError."""
    html = "<html>Test</html>"
    fields_to_extract = ["name"]
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        # Create provider AFTER setting up mock
        provider = DirectProvider(api_key="test-key", provider="anthropic")

        with pytest.raises(LLMError, match="Failed to extract fields"):
            await provider.extract_fields(html, fields_to_extract, schema)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_propose_selectors_not_implemented():
    """GIVEN Phase 1, WHEN calling propose_selectors, THEN raises NotImplementedError."""
    with patch("anthropic.Anthropic"):
        provider = DirectProvider(api_key="test-key", provider="anthropic")

        with pytest.raises(NotImplementedError, match="Phase 2"):
            await provider.propose_selectors([], {}, "context")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repair_selectors_not_implemented():
    """GIVEN Phase 1, WHEN calling repair_selectors, THEN raises NotImplementedError."""
    with patch("anthropic.Anthropic"):
        provider = DirectProvider(api_key="test-key", provider="anthropic")

        with pytest.raises(NotImplementedError, match="Phase 2"):
            await provider.repair_selectors(None, [], [])
