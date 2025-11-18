"""
Storage port - Interface for storage operations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional


class Storage(ABC):
    """Interface for storage operations."""

    @abstractmethod
    async def save_config(
        self, domain: str, page_type: str, config: Dict[str, Any]
    ) -> str:
        """
        Save extraction config.

        Args:
            domain: Domain name
            page_type: Type of page
            config: Config dict to save

        Returns:
            Path where config was saved
        """
        pass

    @abstractmethod
    async def load_config(
        self, domain: str, page_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load extraction config.

        Args:
            domain: Domain name
            page_type: Type of page

        Returns:
            Config dict if exists, None otherwise
        """
        pass

    @abstractmethod
    async def save_html(
        self, domain: str, url: str, html: str, timestamp: datetime
    ) -> str:
        """
        Save raw HTML.

        Args:
            domain: Domain name
            url: Page URL
            html: HTML content
            timestamp: When page was scraped

        Returns:
            Path where HTML was saved
        """
        pass

    @abstractmethod
    async def save_json(
        self, domain: str, url: str, data: Dict[str, Any], timestamp: datetime
    ) -> str:
        """
        Save extracted JSON data.

        Args:
            domain: Domain name
            url: Page URL
            data: Extracted data
            timestamp: When page was scraped

        Returns:
            Path where JSON was saved
        """
        pass

    @abstractmethod
    async def update_coverage_stats(
        self, domain: str, page_type: str, field_name: str, success: bool
    ) -> None:
        """
        Update coverage statistics for a field.

        Args:
            domain: Domain name
            page_type: Type of page
            field_name: Name of field
            success: Whether extraction succeeded
        """
        pass

    @abstractmethod
    async def get_coverage_stats(
        self, domain: str, page_type: str
    ) -> Dict[str, float]:
        """
        Get coverage statistics for a page type.

        Args:
            domain: Domain name
            page_type: Type of page

        Returns:
            Dict mapping field_name -> success_rate (0.0 to 1.0)
        """
        pass
