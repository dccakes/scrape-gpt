"""
HttpxFetcher adapter - Simple HTTP GET using httpx library.
"""

import httpx
from scraper.ports.fetcher import PageFetcher
from scraper.domain.exceptions import FetchError


class HttpxFetcher(PageFetcher):
    """Simple HTTP GET fetcher without JavaScript support."""

    async def fetch(self, url: str, timeout: int = 30000) -> str:
        """
        Fetch page using httpx GET request.

        Args:
            url: URL to fetch
            timeout: Timeout in milliseconds (default: 30000)

        Returns:
            HTML content as string

        Raises:
            FetchError: If fetching fails
        """
        timeout_seconds = timeout / 1000.0

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout_seconds)
                response.raise_for_status()
                return response.text
        except Exception as e:
            raise FetchError(f"Failed to fetch {url}: {e}")
