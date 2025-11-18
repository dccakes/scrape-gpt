"""
LLMProvider port - Interface for LLM operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from scraper.domain.models import PageSample, PageTypeConfig, FieldFailure


class LLMProvider(ABC):
    """Interface for LLM operations."""

    @abstractmethod
    async def propose_selectors(
        self,
        samples: List[PageSample],
        schema: Dict[str, Any],
        domain_context: str,
    ) -> PageTypeConfig:
        """
        Propose XPath selectors based on multiple sample pages.

        Args:
            samples: 3-5 sample pages of the same type
            schema: Expected output schema (JSON Schema format)
            domain_context: Context about the domain

        Returns:
            PageTypeConfig with proposed selectors
        """
        pass

    @abstractmethod
    async def repair_selectors(
        self,
        current_config: PageTypeConfig,
        failures: List[FieldFailure],
        samples: List[PageSample],
    ) -> PageTypeConfig:
        """
        Repair selectors that failed validation.

        Args:
            current_config: Current config with some failing selectors
            failures: List of which fields failed on which pages
            samples: Original sample pages for context

        Returns:
            Updated PageTypeConfig with repaired selectors
        """
        pass

    @abstractmethod
    async def extract_fields(
        self, html: str, fields_to_extract: List[str], schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract only specific fields using LLM.

        Args:
            html: HTML content
            fields_to_extract: List of field names to extract
            schema: Schema for these specific fields

        Returns:
            Dict with only the requested fields populated
        """
        pass
