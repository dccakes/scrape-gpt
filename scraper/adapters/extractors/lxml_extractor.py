"""
LxmlExtractor adapter - XPath/CSS selector extraction using lxml.
"""

from typing import Any, Dict
from lxml import html as lxml_html
from lxml import etree

from scraper.ports.extractor import Extractor
from scraper.domain.models import ExtractionResult, ExtractionMethod
from scraper.domain.exceptions import ExtractionError


class LxmlExtractor(Extractor):
    """XPath/CSS selector extraction using lxml library."""

    def extract(self, html: str, config: Dict[str, Any]) -> ExtractionResult:
        """
        Extract structured data from HTML using XPath/CSS selectors.

        Args:
            html: HTML content to extract from
            config: Extraction configuration with selectors

        Returns:
            ExtractionResult with extracted data and metadata
        """
        try:
            tree = lxml_html.fromstring(html)
        except Exception as e:
            raise ExtractionError(f"Failed to parse HTML: {e}")

        selectors = config.get("selectors", {})
        data = {}
        fields_missing = []
        attempted_selectors = {}

        for field_name, selector_config in selectors.items():
            is_multiple = selector_config.get("multiple", False)

            try:
                # Extract using appropriate method
                if "xpath" in selector_config:
                    selector = selector_config["xpath"]
                    attempted_selectors[field_name] = selector
                    values = tree.xpath(selector)
                elif "css" in selector_config:
                    selector = selector_config["css"]
                    attempted_selectors[field_name] = selector
                    elements = tree.cssselect(selector)
                    values = [self._extract_text(el) for el in elements]
                else:
                    # No valid selector
                    fields_missing.append(field_name)
                    continue

                # Process results
                if is_multiple:
                    # Return list for multiple values
                    data[field_name] = [self._clean_value(v) for v in values]
                    if not data[field_name]:
                        fields_missing.append(field_name)
                else:
                    # Return single value
                    if values and len(values) > 0:
                        cleaned = self._clean_value(values[0])
                        if cleaned:
                            data[field_name] = cleaned
                        else:
                            fields_missing.append(field_name)
                    else:
                        fields_missing.append(field_name)

            except Exception as e:
                # Log error but continue with other fields
                fields_missing.append(field_name)

        # Calculate metadata
        fields_extracted = len([v for v in data.values() if v])
        confidence = (
            fields_extracted / len(selectors) if selectors else 1.0
        )

        return ExtractionResult(
            data=data,
            extraction_method=ExtractionMethod.XPATH,
            confidence=confidence,
            fields_extracted=fields_extracted,
            fields_missing=fields_missing,
            attempted_selectors=attempted_selectors,
        )

    def _extract_text(self, element) -> str:
        """Extract text content from an element."""
        if isinstance(element, str):
            return element
        return element.text_content().strip()

    def _clean_value(self, value: Any) -> Any:
        """Clean extracted value."""
        if isinstance(value, str):
            return value.strip()
        elif isinstance(value, (int, float, bool)):
            return value
        elif hasattr(value, "text_content"):
            return value.text_content().strip()
        else:
            return str(value).strip()
