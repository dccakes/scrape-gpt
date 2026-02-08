"""
ScrapePage use case - End-to-end orchestration.

Orchestrates the full scraping workflow:
1. Fetch HTML
2. Load config
3. Extract with field-level fallback
4. Save results
"""

from datetime import datetime
from typing import Optional
import logging

from scraper.ports.fetcher import PageFetcher
from scraper.ports.llm import LLMProvider
from scraper.ports.storage import Storage
from scraper.ports.alerting import Alerting
from scraper.use_cases.extract_with_fallback import ExtractWithFallback
from scraper.adapters.extractors.lxml_extractor import LxmlExtractor
from scraper.domain.models import (
    ExtractionMethod,
    PageType,
    PageTypeConfig,
    ScrapeResult,
)
from scraper.domain.exceptions import FetchError

logger = logging.getLogger(__name__)


class ScrapePage:
    """
    Orchestrate full page scraping with all enhancements.

    Uses ExtractWithFallback internally for field-level fallback.
    """

    def __init__(
        self,
        fetcher: PageFetcher,
        llm: LLMProvider,
        storage: Storage,
        alerting: Alerting,
    ):
        self.fetcher = fetcher
        self.llm = llm
        self.storage = storage
        self.alerting = alerting

        # Create extractor and fallback use case
        self.extractor = LxmlExtractor()
        self.extract_with_fallback = ExtractWithFallback(
            extractor=self.extractor,
            llm=llm,
            storage=storage,
            alerting=alerting,
        )

    async def execute(
        self,
        url: str,
        domain: str,
        page_type: Optional[PageType] = None,
    ) -> ScrapeResult:
        """
        Scrape a single page.

        Flow:
        1. Fetch HTML
        2. Load config (or generate if missing)
        3. Extract with field-level fallback
        4. Save results + update coverage

        Args:
            url: URL to scrape
            domain: Domain name
            page_type: Type of page (auto-detect if None)

        Returns:
            ScrapeResult with extraction data and metadata
        """
        timestamp = datetime.now()
        logger.info(f"🚀 Scraping: {url}")

        # STEP 1: Fetch HTML
        try:
            html = await self.fetcher.fetch(url)
            logger.info(f"✅ Fetched {len(html)} bytes")
        except FetchError as e:
            logger.error(f"❌ Fetch failed: {e}")
            return ScrapeResult(
                url=url,
                domain=domain,
                page_type=page_type or PageType.UNKNOWN,
                extraction_method=ExtractionMethod.FAILED,
                html_path="",
                json_path="",
                timestamp=timestamp,
                data={},
                success=False,
                error_message=str(e),
            )

        # STEP 2: Auto-detect page type if not provided
        if not page_type:
            page_type = self._detect_page_type(url, html)

        # STEP 3: Load config
        config_dict = await self.storage.load_config(domain, page_type.value)

        if not config_dict:
            logger.warning(f"⚠️ No config found for {domain}/{page_type.value}")
            return ScrapeResult(
                url=url,
                domain=domain,
                page_type=page_type,
                extraction_method=ExtractionMethod.FAILED,
                html_path="",
                json_path="",
                timestamp=timestamp,
                data={},
                success=False,
                error_message=f"No config for {domain}/{page_type.value}",
            )

        config = PageTypeConfig(**config_dict)

        # STEP 4: Extract with field-level fallback
        extraction_result = await self.extract_with_fallback.execute(
            url=url,
            domain=domain,
            page_type=page_type,
            html=html,
            config=config,
        )

        # STEP 5: Save results
        html_path = await self.storage.save_html(
            domain=domain,
            url=url,
            html=html,
            timestamp=timestamp,
        )

        json_path = await self.storage.save_json(
            domain=domain,
            url=url,
            data=extraction_result.data,
            timestamp=timestamp,
        )

        logger.info(f"💾 Saved to: {json_path}")

        return ScrapeResult(
            url=url,
            domain=domain,
            page_type=page_type,
            extraction_method=extraction_result.extraction_method,
            html_path=html_path,
            json_path=json_path,
            timestamp=timestamp,
            data=extraction_result.data,
            success=True,
        )

    def _detect_page_type(self, url: str, html: str) -> PageType:
        """Auto-detect page type based on URL and content."""
        url_lower = url.lower()

        if "quotes.toscrape" in url_lower:
            return PageType.QUOTES_PAGE
        elif "books.toscrape" in url_lower and "/catalogue/" in url_lower:
            return PageType.BOOK_DETAIL
        elif "team" in url_lower or "staff" in url_lower:
            return PageType.TEAM_PAGE
        elif "career" in url_lower or "job" in url_lower:
            return PageType.CAREERS_PAGE
        elif "provider" in url_lower or "physician" in url_lower:
            return PageType.PROVIDER_DIRECTORY
        elif "license" in url_lower:
            return PageType.LICENSE_DIRECTORY
        else:
            return PageType.UNKNOWN
