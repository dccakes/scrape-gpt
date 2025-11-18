"""
Domain models for LLM Web Scraper v2.0

Enhanced with ParserGPT-inspired patterns:
- PageSample for multi-sample config generation
- FieldFailure for targeted repairs
- Coverage tracking fields
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ExtractionMethod(str, Enum):
    """Method used for extraction."""
    XPATH = "xpath"
    XPATH_WITH_LLM_FALLBACK = "xpath_with_llm_fallback"  # NEW in v2.0
    LLM_FALLBACK = "llm_fallback"
    LLM_DIRECT = "llm_direct"
    FAILED = "failed"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PageType(str, Enum):
    """Known page types."""
    TEAM_PAGE = "team_page"
    CAREERS_PAGE = "careers_page"
    PROVIDER_DIRECTORY = "provider_directory"
    LICENSE_DIRECTORY = "license_directory"
    UNKNOWN = "unknown"


# NEW in v2.0: Multi-sample config generation
class PageSample(BaseModel):
    """A sample page for config generation."""
    url: HttpUrl
    html: str
    fetched_at: datetime = Field(default_factory=datetime.now)


# NEW in v2.0: Targeted repair
class FieldFailure(BaseModel):
    """A field that failed extraction on a specific sample."""
    field_name: str
    sample_url: HttpUrl
    html_snippet: str
    current_selector: Optional[str] = None


class Person(BaseModel):
    """A person extracted from a web page."""
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class ExtractionResult(BaseModel):
    """Result of data extraction - Enhanced in v2.0."""
    data: Dict[str, Any]
    extraction_method: ExtractionMethod
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    fields_extracted: int = 0
    fields_missing: List[str] = Field(default_factory=list)
    
    # NEW in v2.0
    llm_fields_used: List[str] = Field(default_factory=list)
    attempted_selectors: Dict[str, str] = Field(default_factory=dict)


class PageTypeConfig(BaseModel):
    """Configuration for extracting a specific page type - Enhanced in v2.0."""
    version: str
    domain: str
    page_type: PageType
    selectors: Dict[str, Dict[str, Any]]
    schema: Dict[str, Any]
    
    # NEW in v2.0: Coverage tracking
    coverage_stats: Dict[str, float] = Field(default_factory=dict)
    last_validated: Optional[datetime] = None
    total_pages_tested: int = 0


# NEW in v2.0
class ConfigGenerationResult(BaseModel):
    """Result of config generation."""
    config: PageTypeConfig
    final_coverage: float
    iterations_needed: int
    config_path: str
    sample_count: int


class ScrapeResult(BaseModel):
    """Result of scraping a single page."""
    url: str
    domain: str
    page_type: PageType
    extraction_method: ExtractionMethod
    html_path: str
    json_path: str
    timestamp: datetime
    data: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
