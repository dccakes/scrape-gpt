"""
Domain exceptions for LLM Web Scraper.

All custom exceptions inherit from ScraperError base class.
"""


class ScraperError(Exception):
    """Base exception for all scraper errors."""
    pass


class FetchError(ScraperError):
    """Raised when page fetching fails."""
    pass


class ExtractionError(ScraperError):
    """Raised when extraction fails."""
    pass


class ConfigGenerationError(ScraperError):
    """Raised when config generation fails."""
    pass


class LLMError(ScraperError):
    """Raised when LLM operations fail."""
    pass


class StorageError(ScraperError):
    """Raised when storage operations fail."""
    pass
