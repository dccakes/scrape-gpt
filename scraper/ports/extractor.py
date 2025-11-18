"""
Extractor port - Interface for extracting structured data from HTML.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from scraper.domain.models import ExtractionResult


class Extractor(ABC):
    """Interface for extracting structured data from HTML."""

    @abstractmethod
    def extract(self, html: str, config: Dict[str, Any]) -> ExtractionResult:
        """
        Extract structured data from HTML using provided config.

        Args:
            html: HTML content to extract from
            config: Extraction configuration with selectors

        Returns:
            ExtractionResult with extracted data and metadata

        Raises:
            ExtractionError: If extraction fails completely
        """
        pass
