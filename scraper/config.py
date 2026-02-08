"""
Dependency Injection Container.

Resolves adapters based on environment variables.
Allows swapping adapters with zero code changes.
"""

import os
from functools import cached_property
from dotenv import load_dotenv

from scraper.ports.fetcher import PageFetcher
from scraper.ports.extractor import Extractor
from scraper.ports.llm import LLMProvider
from scraper.ports.storage import Storage
from scraper.ports.alerting import Alerting

# Adapters
from scraper.adapters.fetchers.httpx_fetcher import HttpxFetcher
from scraper.adapters.extractors.lxml_extractor import LxmlExtractor
from scraper.adapters.storage.local_storage import LocalStorage
from scraper.adapters.alerting.console_alerting import ConsoleAlerting
from scraper.adapters.llm.direct_provider import DirectProvider

# Load environment variables
load_dotenv()


class Container:
    """
    DI Container for resolving dependencies.

    Usage:
        from scraper.config import container

        scraper = ScrapePage(
            fetcher=container.fetcher,
            llm=container.llm,
            storage=container.storage,
            alerting=container.alerting,
        )
    """

    @cached_property
    def fetcher(self) -> PageFetcher:
        """Get configured PageFetcher."""
        fetcher_type = os.getenv("FETCHER", "httpx")

        if fetcher_type == "httpx":
            return HttpxFetcher()
        elif fetcher_type == "playwright":
            # Phase 3: Import PlaywrightFetcher when implemented
            raise NotImplementedError("PlaywrightFetcher is a Phase 3 feature")
        else:
            raise ValueError(f"Unknown fetcher type: {fetcher_type}")

    @cached_property
    def extractor(self) -> Extractor:
        """Get configured Extractor."""
        return LxmlExtractor()

    @cached_property
    def llm(self) -> LLMProvider:
        """Get configured LLMProvider."""
        provider_type = os.getenv("LLM_PROVIDER", "direct")

        if provider_type == "direct":
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required for DirectProvider"
                )
            return DirectProvider(api_key=api_key, provider="anthropic")
        elif provider_type == "pocketflow":
            # Phase 3: Import PocketFlowProvider when implemented
            raise NotImplementedError("PocketFlowProvider is a Phase 3 feature")
        else:
            raise ValueError(f"Unknown LLM provider type: {provider_type}")

    @cached_property
    def storage(self) -> Storage:
        """Get configured Storage."""
        storage_type = os.getenv("STORAGE", "local")

        if storage_type == "local":
            base_path = os.getenv("DATA_PATH", "data")
            return LocalStorage(base_path=base_path)
        elif storage_type == "s3":
            # Phase 3: Import S3Storage when implemented
            raise NotImplementedError("S3Storage is a Phase 3 feature")
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")

    @cached_property
    def alerting(self) -> Alerting:
        """Get configured Alerting."""
        alerting_type = os.getenv("ALERTING", "console")

        if alerting_type == "console":
            return ConsoleAlerting()
        elif alerting_type == "knock":
            # Phase 3: Import KnockAlerting when implemented
            raise NotImplementedError("KnockAlerting is a Phase 3 feature")
        else:
            raise ValueError(f"Unknown alerting type: {alerting_type}")


# Singleton container instance
container = Container()
