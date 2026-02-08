"""
DirectProvider adapter - Direct Anthropic/OpenAI API calls.
"""

import json
from typing import Any, Dict, List

from scraper.ports.llm import LLMProvider
from scraper.domain.models import PageSample, PageTypeConfig, FieldFailure
from scraper.domain.exceptions import LLMError


class DirectProvider(LLMProvider):
    """Direct Anthropic/OpenAI API calls for LLM operations."""

    def __init__(self, api_key: str, provider: str = "anthropic"):
        """
        Initialize with API key and provider.

        Args:
            api_key: API key for the LLM provider
            provider: "anthropic" or "openai" (default: anthropic)
        """
        self.api_key = api_key
        self.provider = provider

        if provider == "anthropic":
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key)
        elif provider == "openai":
            import openai

            self.client = openai.OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def extract_fields(
        self, html: str, fields_to_extract: List[str], schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract only specific fields using LLM.

        This is the key Phase 1 feature for field-level fallback.

        Args:
            html: HTML content
            fields_to_extract: List of field names to extract
            schema: Schema for these specific fields

        Returns:
            Dict with only the requested fields populated
        """
        # Truncate HTML to 12000 characters
        truncated_html = html[:12000]
        if len(html) > 12000:
            truncated_html += "..."

        # Build minimal schema for requested fields only
        minimal_schema = {
            "type": "object",
            "properties": {
                field: schema["properties"][field]
                for field in fields_to_extract
                if field in schema.get("properties", {})
            },
        }

        prompt = f"""Extract ONLY these fields from the HTML:
{fields_to_extract}

Schema:
{json.dumps(minimal_schema, indent=2)}

HTML:
{truncated_html}

Return ONLY valid JSON matching the schema exactly.
If a field cannot be found, use null or an empty string.
Do not include any explanatory text, only the JSON object."""

        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}],
                )

                # Extract JSON from response
                content = response.content[0].text
                result = json.loads(content)
                return result

            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                result = json.loads(content)
                return result

        except Exception as e:
            raise LLMError(f"Failed to extract fields with {self.provider}: {e}")

    async def propose_selectors(
        self,
        samples: List[PageSample],
        schema: Dict[str, Any],
        domain_context: str,
    ) -> PageTypeConfig:
        """
        Propose XPath selectors based on multiple sample pages.

        NOTE: This is a Phase 2 feature. In Phase 1, configs are created manually.
        """
        raise NotImplementedError(
            "propose_selectors() is a Phase 2 feature. "
            "In Phase 1, create configs manually."
        )

    async def repair_selectors(
        self,
        current_config: PageTypeConfig,
        failures: List[FieldFailure],
        samples: List[PageSample],
    ) -> PageTypeConfig:
        """
        Repair selectors that failed validation.

        NOTE: This is a Phase 2 feature. In Phase 1, configs are created manually.
        """
        raise NotImplementedError(
            "repair_selectors() is a Phase 2 feature. "
            "In Phase 1, configs are maintained manually."
        )
