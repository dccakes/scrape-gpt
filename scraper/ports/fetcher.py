"""
PageFetcher port - Interface for fetching web pages.
"""

from abc import ABC, abstractmethod


class PageFetcher(ABC):
    """Interface for fetching web pages."""

    @abstractmethod
    async def fetch(self, url: str, timeout: int = 30000) -> str:
        """
        Fetch a page and return its HTML content.

        Args:
            url: URL to fetch
            timeout: Timeout in milliseconds (default: 30000)

        Returns:
            HTML content as string

        Raises:
            FetchError: If fetching fails
        """
        pass
