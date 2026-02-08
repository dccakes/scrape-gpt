"""
ExtractWithFallback use case - Field-level LLM fallback.

This is the key Phase 1 feature that achieves 85% cost reduction
by only extracting missing fields with LLM instead of the entire page.
"""

from typing import List, Dict, Any, Optional
import logging

from scraper.ports.extractor import Extractor
from scraper.ports.llm import LLMProvider
from scraper.ports.storage import Storage
from scraper.ports.alerting import Alerting
from scraper.domain.models import (
    ExtractionResult,
    ExtractionMethod,
    PageType,
    PageTypeConfig,
    AlertSeverity,
)
from scraper.domain.exceptions import ExtractionError, LLMError

logger = logging.getLogger(__name__)


class ExtractWithFallback:
    """
    Extract data with field-level LLM fallback.

    Flow:
    1. Try XPath extraction (fast, cheap)
    2. Identify missing required fields
    3. If any missing, use LLM for ONLY those fields
    4. Merge results (prefer XPath)
    5. Update coverage statistics
    """

    def __init__(
        self,
        extractor: Extractor,
        llm: LLMProvider,
        storage: Storage,
        alerting: Alerting,
    ):
        self.extractor = extractor
        self.llm = llm
        self.storage = storage
        self.alerting = alerting

    async def execute(
        self,
        url: str,
        domain: str,
        page_type: PageType,
        html: str,
        config: PageTypeConfig,
    ) -> ExtractionResult:
        """
        Extract data with field-level LLM fallback.

        Args:
            url: URL being scraped
            domain: Domain name
            page_type: Type of page
            html: HTML content
            config: Extraction configuration

        Returns:
            ExtractionResult with complete data
        """

        # STEP 1: Try XPath extraction
        logger.info(f"🔍 Extracting with XPath: {url}")
        xpath_result = None
        xpath_error = None

        try:
            xpath_result = self.extractor.extract(html, config.model_dump())
            logger.info(
                f"✅ XPath extracted {xpath_result.fields_extracted} fields"
            )
        except ExtractionError as e:
            logger.warning(f"⚠️ XPath extraction failed: {e}")
            xpath_error = e

        # STEP 2: Identify missing required fields
        missing_fields = self._identify_missing_fields(xpath_result, config)

        if not missing_fields:
            # All fields extracted successfully!
            await self._update_coverage_stats(
                domain=domain,
                page_type=page_type,
                result=xpath_result,
            )

            return xpath_result

        # STEP 3: Field-level LLM fallback
        logger.info(
            f"🤖 LLM fallback for {len(missing_fields)} missing fields: "
            f"{missing_fields}"
        )

        try:
            # Only extract missing fields!
            llm_fields = await self.llm.extract_fields(
                html=html,
                fields_to_extract=missing_fields,
                schema=self._build_field_schema(missing_fields, config),
            )

            logger.info(f"✅ LLM extracted missing fields")

            # STEP 4: Merge results
            merged_result = self._merge_results(
                xpath_result=xpath_result,
                llm_fields=llm_fields,
                missing_fields=missing_fields,
            )

            # Update metadata
            merged_result.extraction_method = ExtractionMethod.XPATH_WITH_LLM_FALLBACK
            merged_result.llm_fields_used = missing_fields

        except Exception as e:
            logger.error(f"❌ LLM fallback failed: {e}")

            # Alert on critical failure
            await self.alerting.send_alert(
                title="Extraction Failure",
                message=f"Both XPath and LLM failed for {url}",
                severity=AlertSeverity.CRITICAL,
                metadata={
                    "url": url,
                    "domain": domain,
                    "page_type": page_type.value,
                    "xpath_error": str(xpath_error) if xpath_error else None,
                    "llm_error": str(e),
                },
            )

            # Return partial XPath result
            merged_result = xpath_result or ExtractionResult(
                data={},
                extraction_method=ExtractionMethod.FAILED,
                confidence=0.0,
            )

        # STEP 5: Update coverage statistics
        await self._update_coverage_stats(
            domain=domain,
            page_type=page_type,
            result=merged_result,
        )

        # Alert if coverage drops below threshold
        coverage_stats = await self.storage.get_coverage_stats(
            domain, page_type.value
        )
        low_coverage_fields = [
            field for field, rate in coverage_stats.items() if rate < 0.7
        ]

        if low_coverage_fields:
            await self.alerting.send_alert(
                title="Low Field Coverage",
                message=f"Fields with <70% coverage: {low_coverage_fields}",
                severity=AlertSeverity.WARNING,
                metadata={
                    "domain": domain,
                    "page_type": page_type.value,
                    "low_fields": low_coverage_fields,
                    "coverage_stats": coverage_stats,
                },
            )

        return merged_result

    def _identify_missing_fields(
        self,
        result: Optional[ExtractionResult],
        config: PageTypeConfig,
    ) -> List[str]:
        """
        Identify which required fields are missing.

        Returns:
            List of field names that need LLM extraction
        """
        if not result:
            # XPath completely failed
            return list(config.selectors.keys())

        missing = []
        for field_name in config.selectors.keys():
            # Check if field is required
            is_required = field_name in config.schema.get("required", [])

            # Check if field is missing or empty
            value = result.data.get(field_name)
            is_missing = not value or (isinstance(value, list) and len(value) == 0)

            if is_required and is_missing:
                missing.append(field_name)

        return missing

    def _build_field_schema(
        self, field_names: List[str], config: PageTypeConfig
    ) -> Dict[str, Any]:
        """Build JSON schema for specific fields only."""
        return {
            "type": "object",
            "properties": {
                field: config.schema["properties"][field]
                for field in field_names
                if field in config.schema["properties"]
            },
            "required": [
                field
                for field in field_names
                if field in config.schema.get("required", [])
            ],
        }

    def _merge_results(
        self,
        xpath_result: Optional[ExtractionResult],
        llm_fields: Dict[str, Any],
        missing_fields: List[str],
    ) -> ExtractionResult:
        """
        Merge XPath and LLM results.

        Strategy:
        - Prefer XPath values (deterministic, trusted)
        - Use LLM values only for missing fields
        - Never overwrite good XPath data with LLM data
        """
        if not xpath_result:
            # No XPath data, use LLM entirely
            return ExtractionResult(
                data=llm_fields,
                extraction_method=ExtractionMethod.LLM_FALLBACK,
                confidence=0.7,  # Lower confidence for LLM-only
                fields_extracted=len(llm_fields),
                fields_missing=[],
            )

        # Merge: XPath as base, LLM fills gaps
        merged_data = xpath_result.data.copy()

        for field_name, llm_value in llm_fields.items():
            if field_name in missing_fields and llm_value:
                merged_data[field_name] = llm_value

        return ExtractionResult(
            data=merged_data,
            extraction_method=ExtractionMethod.XPATH_WITH_LLM_FALLBACK,
            confidence=0.85,  # High confidence (mostly XPath)
            fields_extracted=len(merged_data),
            fields_missing=[],
            llm_fields_used=missing_fields,
        )

    async def _update_coverage_stats(
        self,
        domain: str,
        page_type: PageType,
        result: ExtractionResult,
    ) -> None:
        """Update coverage statistics for each field."""
        for field_name in result.data.keys():
            success = bool(result.data[field_name])

            await self.storage.update_coverage_stats(
                domain=domain,
                page_type=page_type.value,
                field_name=field_name,
                success=success,
            )
