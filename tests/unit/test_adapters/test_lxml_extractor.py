"""
Unit tests for LxmlExtractor adapter.
"""

import pytest
from scraper.adapters.extractors.lxml_extractor import LxmlExtractor
from scraper.domain.models import ExtractionMethod


@pytest.mark.unit
def test_extract_with_xpath():
    """GIVEN HTML and XPath config, WHEN extracting, THEN data is extracted."""
    html = """
    <html>
        <body>
            <h1>John Doe</h1>
            <div class="title">Chief Technology Officer</div>
            <a href="mailto:john@example.com">john@example.com</a>
        </body>
    </html>
    """

    config = {
        "selectors": {
            "name": {"xpath": "//h1/text()"},
            "title": {"xpath": "//div[@class='title']/text()"},
            "email": {"xpath": "//a[starts-with(@href, 'mailto:')]/text()"},
        }
    }

    extractor = LxmlExtractor()
    result = extractor.extract(html, config)

    assert result.data["name"] == "John Doe"
    assert result.data["title"] == "Chief Technology Officer"
    assert result.data["email"] == "john@example.com"
    assert result.extraction_method == ExtractionMethod.XPATH
    assert result.fields_extracted == 3
    assert len(result.fields_missing) == 0


@pytest.mark.unit
def test_extract_with_css():
    """GIVEN HTML and CSS config, WHEN extracting, THEN data is extracted."""
    html = """
    <html>
        <body>
            <h1 class="name">Jane Smith</h1>
            <div class="role">CEO</div>
        </body>
    </html>
    """

    config = {
        "selectors": {
            "name": {"css": "h1.name"},
            "title": {"css": "div.role"},
        }
    }

    extractor = LxmlExtractor()
    result = extractor.extract(html, config)

    assert result.data["name"] == "Jane Smith"
    assert result.data["title"] == "CEO"


@pytest.mark.unit
def test_extract_multiple_values():
    """GIVEN config with multiple=true, WHEN extracting, THEN returns list."""
    html = """
    <html>
        <body>
            <ul>
                <li>Skill 1</li>
                <li>Skill 2</li>
                <li>Skill 3</li>
            </ul>
        </body>
    </html>
    """

    config = {
        "selectors": {
            "skills": {"xpath": "//li/text()", "multiple": True},
        }
    }

    extractor = LxmlExtractor()
    result = extractor.extract(html, config)

    assert result.data["skills"] == ["Skill 1", "Skill 2", "Skill 3"]


@pytest.mark.unit
def test_extract_with_missing_fields():
    """GIVEN selector that doesn't match, WHEN extracting, THEN field is in fields_missing."""
    html = """
    <html>
        <body>
            <h1>John Doe</h1>
        </body>
    </html>
    """

    config = {
        "selectors": {
            "name": {"xpath": "//h1/text()"},
            "email": {"xpath": "//a[contains(@href, 'mailto')]/text()"},
            "phone": {"xpath": "//span[@class='phone']/text()"},
        }
    }

    extractor = LxmlExtractor()
    result = extractor.extract(html, config)

    assert result.data["name"] == "John Doe"
    assert "email" not in result.data or result.data["email"] is None
    assert "phone" not in result.data or result.data["phone"] is None
    assert "email" in result.fields_missing
    assert "phone" in result.fields_missing
    assert result.fields_extracted == 1


@pytest.mark.unit
def test_extract_records_attempted_selectors():
    """GIVEN config, WHEN extracting, THEN attempted_selectors is populated."""
    html = "<html><body><h1>Test</h1></body></html>"

    config = {
        "selectors": {
            "name": {"xpath": "//h1/text()"},
            "email": {"xpath": "//a/text()"},
        }
    }

    extractor = LxmlExtractor()
    result = extractor.extract(html, config)

    assert "name" in result.attempted_selectors
    assert result.attempted_selectors["name"] == "//h1/text()"
    assert "email" in result.attempted_selectors
    assert result.attempted_selectors["email"] == "//a/text()"
