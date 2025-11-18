"""
Unit tests for HttpxFetcher adapter.
"""

import pytest
from unittest.mock import AsyncMock, patch
from scraper.adapters.fetchers.httpx_fetcher import HttpxFetcher
from scraper.domain.exceptions import FetchError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_httpx_fetcher_fetches_successfully():
    """GIVEN valid URL, WHEN fetching, THEN returns HTML."""
    fetcher = HttpxFetcher()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_get.return_value = mock_response

        html = await fetcher.fetch("https://example.com")

        assert html == "<html><body>Test</body></html>"
        mock_get.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_httpx_fetcher_raises_on_404():
    """GIVEN URL that returns 404, WHEN fetching, THEN raises FetchError."""
    fetcher = HttpxFetcher()

    with patch("httpx.AsyncClient.get") as mock_get:
        import httpx as httpx_module
        mock_get.side_effect = httpx_module.HTTPStatusError(
            "404 Not Found",
            request=AsyncMock(),
            response=AsyncMock(status_code=404),
        )

        with pytest.raises(FetchError, match="Failed to fetch"):
            await fetcher.fetch("https://example.com/notfound")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_httpx_fetcher_raises_on_timeout():
    """GIVEN URL that times out, WHEN fetching, THEN raises FetchError."""
    fetcher = HttpxFetcher()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = Exception("Timeout")

        with pytest.raises(FetchError, match="Failed to fetch"):
            await fetcher.fetch("https://example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_httpx_fetcher_respects_timeout():
    """GIVEN custom timeout, WHEN fetching, THEN passes timeout to httpx."""
    fetcher = HttpxFetcher()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test</html>"
        mock_get.return_value = mock_response

        await fetcher.fetch("https://example.com", timeout=60000)

        # Verify timeout was passed (in seconds, converted from milliseconds)
        call_kwargs = mock_get.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == 60.0
