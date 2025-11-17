# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an intelligent web scraping system that combines deterministic XPath extraction with LLM-powered adaptation. The LLM acts as a "compiler" that generates extraction rules, not as a runtime extractor. This approach dramatically reduces cost while maintaining high accuracy.

**Key Features:**
- Multi-sample config generation (3-5 pages for robust selectors)
- Field-level LLM fallback (85% cost reduction vs page-level)
- Validation + repair loops (quality gates)
- Coverage tracking (health monitoring)

**Performance Targets:**
- Config generation: <$0.15 per page type
- Runtime extraction: >85% XPath success rate
- LLM cost: <$0.003 per page (field-level fallback)
- Coverage: >80% selector reliability

## Essential Development Commands

### Environment Setup
- `make setup` - Install dependencies with uv and configure pre-commit hooks
- `make install` - Install project dependencies only
- `make clean` - Clean up virtual environment and caches

### Testing & Code Quality
- `make test` - Run unit tests with pytest (excludes integration tests)
- `make test-integration` - Run integration tests
- `make test-all` - Run all tests
- `make lint` - Run ruff and mypy checks
- `make lint-fix` - Auto-fix linting issues with ruff
- `make format` - Format code with black

### Development
- `make run` - Run the scraper CLI
- `make shell` - Start IPython shell with imports

## Architecture Overview

### Core Architectural Principles

**Clean Architecture:** Domain-driven design with clear separation of concerns
- Domain layer (business logic) is independent of infrastructure
- Dependencies point inward: Use Cases → Ports → Domain
- Adapters implement ports and connect to external systems

**YAGNI (You Aren't Gonna Need It):** Build only what's specified
- No speculative features
- No premature optimization
- Stick to the specifications (see `/docs/`)

**Test-Driven Development:** All code written via Red-Green-Refactor
- Write failing test first (RED)
- Write minimal code to pass (GREEN)
- Refactor if valuable (REFACTOR)

### System Architecture

The system follows a **three-phase pipeline**:

```
Phase 1: CONFIG GENERATION         Phase 2: EXTRACTION              Phase 3: STORAGE
Multi-Sample Learning       →      Deterministic XPath       →      HTML + JSON
(LLM generates selectors)          + Field-Level Fallback           (with coverage stats)
```

### Directory Structure

```
scrape-gpt/
├── scraper/
│   ├── domain/             # Domain models and business logic
│   │   ├── models.py      # Pydantic models (PageSample, ExtractionResult, etc.)
│   │   └── exceptions.py  # Domain-specific exceptions
│   ├── ports/              # Interface definitions (ABC classes)
│   │   ├── fetcher.py     # PageFetcher interface
│   │   ├── extractor.py   # Extractor interface
│   │   ├── llm.py         # LLMProvider interface
│   │   ├── storage.py     # Storage interface
│   │   └── alerting.py    # Alerting interface
│   ├── adapters/           # Port implementations
│   │   ├── fetchers/
│   │   │   ├── httpx_fetcher.py      # Simple HTTP GET
│   │   │   └── playwright_fetcher.py # Full browser with JS
│   │   ├── extractors/
│   │   │   └── lxml_extractor.py     # XPath/CSS extraction
│   │   ├── llm/
│   │   │   ├── direct_provider.py    # Direct Anthropic/OpenAI
│   │   │   └── pocketflow_provider.py # PocketFlow orchestration
│   │   ├── storage/
│   │   │   ├── local_storage.py      # Local filesystem
│   │   │   └── s3_storage.py         # AWS S3
│   │   └── alerting/
│   │       ├── console_alerting.py   # Console output
│   │       └── knock_alerting.py     # Knock.app
│   ├── use_cases/          # Business workflows
│   │   ├── generate_config.py        # Phase 1: Config generation
│   │   ├── extract_with_fallback.py  # Phase 2: Extraction
│   │   └── scrape_page.py            # End-to-end orchestration
│   ├── config.py           # DI Container
│   └── cli.py              # Command-line interface
├── tests/
│   ├── unit/               # Fast, isolated tests
│   ├── integration/        # Real adapters
│   └── e2e/                # Full stack
├── docs/
│   ├── SYSTEM_DESIGN_LLM_Web_Scraper_v2.0.md  # Complete spec
│   ├── ParserGPT_Comparison.md                # Design rationale
│   └── adr/                                    # Architecture decisions
└── data/                   # Generated configs and scraped data
```

### Key Architectural Patterns

#### Clean Architecture Layers

**1. Domain Layer** (`scraper/domain/`)
- Pure business logic, no external dependencies
- Models: `PageSample`, `ExtractionResult`, `PageTypeConfig`, etc.
- Exceptions: `FetchError`, `ExtractionError`, `ConfigGenerationError`

**2. Ports Layer** (`scraper/ports/`)
- Abstract interfaces (ABC classes)
- Define contracts between domain and adapters
- Five core ports: `PageFetcher`, `Extractor`, `LLMProvider`, `Storage`, `Alerting`

**3. Adapters Layer** (`scraper/adapters/`)
- Concrete implementations of ports
- Each adapter <150 lines (KISS principle)
- Swappable via `.env` configuration

**4. Use Cases Layer** (`scraper/use_cases/`)
- Orchestrate business workflows
- Depend only on ports, never on adapters
- Stateless with dependency injection

#### Port Definitions

**PageFetcher:** Fetch HTML from URLs
```python
class PageFetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str, timeout: int = 30000) -> str:
        pass
```

**Extractor:** Extract structured data using XPath/CSS
```python
class Extractor(ABC):
    @abstractmethod
    def extract(self, html: str, config: Dict[str, Any]) -> ExtractionResult:
        pass
```

**LLMProvider:** LLM operations (config generation, field extraction)
```python
class LLMProvider(ABC):
    @abstractmethod
    async def propose_selectors(
        self, samples: List[PageSample], schema: Dict[str, Any], domain_context: str
    ) -> PageTypeConfig:
        pass

    @abstractmethod
    async def repair_selectors(
        self, current_config: PageTypeConfig, failures: List[FieldFailure], samples: List[PageSample]
    ) -> PageTypeConfig:
        pass

    @abstractmethod
    async def extract_fields(
        self, html: str, fields_to_extract: List[str], schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass
```

**Storage:** Save/load configs, HTML, JSON, and coverage stats
```python
class Storage(ABC):
    @abstractmethod
    async def save_config(self, domain: str, page_type: str, config: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def load_config(self, domain: str, page_type: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_coverage_stats(self, domain: str, page_type: str, field_name: str, success: bool) -> None:
        pass

    @abstractmethod
    async def get_coverage_stats(self, domain: str, page_type: str) -> Dict[str, float]:
        pass
```

**Alerting:** Send notifications
```python
class Alerting(ABC):
    @abstractmethod
    async def send_alert(
        self, title: str, message: str, severity: AlertSeverity, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        pass
```

#### Use Cases

**1. GenerateConfig** (Phase 1: Config Generation)
- Collects 3-5 sample pages
- LLM proposes XPath selectors
- Validates selectors on all samples
- Repairs failing selectors (up to 3 iterations)
- Saves config with >80% coverage

**2. ExtractWithFallback** (Phase 2: Extraction)
- Tries XPath extraction first (fast, cheap)
- Identifies missing required fields
- Uses LLM for only missing fields (field-level fallback)
- Merges results (prefers deterministic)
- Updates coverage statistics

**3. ScrapePage** (End-to-End Orchestration)
- Fetches HTML
- Loads or generates config
- Extracts with field-level fallback
- Saves HTML + JSON + updates coverage

#### Dependency Injection Container

The `Container` class in `config.py` resolves adapters based on `.env` variables:

```python
# .env
FETCHER=playwright
STORAGE=local
LLM_PROVIDER=direct
ALERTING=console

# Usage
from scraper.config import container

scraper = ScrapePage(
    fetcher=container.fetcher,       # PlaywrightFetcher
    extractor=container.extractor,   # LxmlExtractor
    llm=container.llm,               # DirectProvider
    storage=container.storage,       # LocalStorage
    alerting=container.alerting      # ConsoleAlerting
)
```

**Swap providers with zero code changes!**

### Data Flow & Models

#### Core Domain Models

**PageSample:** Sample page for config generation
```python
class PageSample(BaseModel):
    url: HttpUrl
    html: str
    fetched_at: datetime
```

**FieldFailure:** Field that failed extraction
```python
class FieldFailure(BaseModel):
    field_name: str
    sample_url: HttpUrl
    html_snippet: str
    current_selector: Optional[str]
```

**ExtractionResult:** Result of extraction
```python
class ExtractionResult(BaseModel):
    data: Dict[str, Any]
    extraction_method: ExtractionMethod
    confidence: float
    fields_extracted: int
    fields_missing: List[str]
    llm_fields_used: List[str]  # NEW in v2.0
    attempted_selectors: Dict[str, str]
```

**PageTypeConfig:** Configuration for a page type
```python
class PageTypeConfig(BaseModel):
    version: str
    domain: str
    page_type: PageType
    selectors: Dict[str, Dict[str, Any]]
    schema: Dict[str, Any]
    coverage_stats: Dict[str, float]  # NEW in v2.0
    last_validated: Optional[datetime]
    total_pages_tested: int
```

#### Extraction Methods

- `XPATH`: Pure XPath extraction
- `XPATH_WITH_LLM_FALLBACK`: XPath + field-level LLM (most common)
- `LLM_FALLBACK`: LLM for missing fields only
- `LLM_DIRECT`: Full LLM extraction (rare, expensive)
- `FAILED`: Both XPath and LLM failed

## Testing Strategy

### Test-Driven Development (MANDATORY)

**Every feature MUST follow Red-Green-Refactor:**

1. **RED:** Write a failing test based on specification
   - Test defines the behavior we want
   - Test should fail because feature doesn't exist yet
   - NEVER write production code without a failing test first

2. **GREEN:** Write minimal code to make test pass
   - Implement only what's needed to satisfy the test
   - Resist the urge to add extra features
   - Focus on making the test pass, not on perfect code

3. **REFACTOR:** Improve code quality while keeping tests green
   - Remove duplication
   - Improve names
   - Extract methods/classes if valuable
   - Tests must still pass after refactoring

### Test Organization

```
tests/
├── unit/                   # Fast, isolated (mock dependencies)
│   ├── test_domain/
│   ├── test_adapters/
│   └── test_use_cases/
├── integration/            # Real adapters (no mocks)
│   ├── test_llm/
│   ├── test_storage/
│   └── test_extraction/
└── e2e/                    # Full stack (real URLs)
    └── test_full_flow.py
```

**Test Categories:**
- `unit`: Fast (<1s total), no I/O, mock all ports
- `integration`: Slower (seconds), real adapters, test boundaries
- `e2e`: Slowest (minutes), full system, real websites

**Example Test Structure:**
```python
# tests/unit/test_use_cases/test_extract_with_fallback.py

async def test_field_level_fallback_only_extracts_missing_fields():
    """GIVEN XPath extracted 9/10 fields, WHEN LLM fallback runs,
    THEN only the missing field is sent to LLM."""
    # Arrange
    extractor = Mock(Extractor)
    llm = Mock(LLMProvider)
    storage = Mock(Storage)
    alerting = Mock(Alerting)

    xpath_result = ExtractionResult(
        data={"name": "John", "title": "CTO", "phone": "555-1234"},
        extraction_method=ExtractionMethod.XPATH,
        fields_missing=["email"]  # Only email is missing
    )
    extractor.extract.return_value = xpath_result

    llm.extract_fields.return_value = {"email": "john@example.com"}

    use_case = ExtractWithFallback(extractor, llm, storage, alerting)

    # Act
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        html="<html>...</html>",
        config=mock_config
    )

    # Assert
    llm.extract_fields.assert_called_once_with(
        html="<html>...</html>",
        fields_to_extract=["email"],  # Only missing field!
        schema={"email": {"type": "string"}}
    )
    assert result.data["email"] == "john@example.com"
    assert result.llm_fields_used == ["email"]
```

### Running Tests
```bash
# Run all unit tests
make test

# Run specific test file
pytest tests/unit/test_use_cases/test_extract_with_fallback.py -v

# Run tests matching a pattern
pytest -k "field_level" -v

# Run with coverage
pytest --cov=scraper tests/

# Run integration tests (slower)
make test-integration

# Run all tests
make test-all
```

## Code Style & Standards

### Code Structure

**No nested if/else:** Use early returns and guard clauses
```python
# BAD
def process(data):
    if data:
        if data.valid:
            return process_valid(data)
        else:
            return handle_invalid(data)
    else:
        return None

# GOOD
def process(data):
    if not data:
        return None

    if not data.valid:
        return handle_invalid(data)

    return process_valid(data)
```

**Maximum nesting depth: 2 levels**

**Small, focused functions:**
- Each function does one thing
- Functions should be <20 lines when possible
- Extract complex logic into named helper functions

### Naming Conventions

- Functions: `snake_case`, verb-based (`calculate_coverage`, `validate_config`)
- Classes: `PascalCase` (`PageFetcher`, `ExtractWithFallback`)
- Constants: `UPPER_SNAKE_CASE` for true constants
- Files: `snake_case.py`
- Test files: `test_*.py`

### Type Hints

**Required for all function signatures:**
```python
def calculate_coverage(results: List[ExtractionResult], schema: Dict[str, Any]) -> float:
    """Calculate overall coverage across all results."""
    ...

async def extract_fields(
    self,
    html: str,
    fields_to_extract: List[str],
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract only specific fields using LLM."""
    ...
```

### Comments & Documentation

**Code should be self-documenting.** Comments indicate unclear code.

**Docstrings:** Use for public APIs and complex algorithms
```python
async def generate_config_with_validation(
    domain: str,
    page_type: PageType,
    samples: List[PageSample],
    target_schema: Dict[str, Any],
    coverage_threshold: float = 0.8,
    max_iterations: int = 3
) -> PageTypeConfig:
    """
    Generate config with validation loop.

    Flow:
    1. Propose selectors based on samples
    2. Validate against all samples
    3. If coverage < 80%, repair with targeted fixes
    4. Repeat up to 3 times

    Args:
        domain: Domain name
        page_type: Type of page
        samples: 3-5 sample pages
        target_schema: Expected output schema
        coverage_threshold: Minimum acceptable coverage (default: 0.8)
        max_iterations: Max repair iterations (default: 3)

    Returns:
        Validated PageTypeConfig with high confidence
    """
```

**Inline comments:** Only when absolutely necessary to explain "why", never "what"

### Error Handling

**Use custom domain exceptions:**
```python
# scraper/domain/exceptions.py
class ScraperError(Exception):
    """Base exception for scraper errors."""

class FetchError(ScraperError):
    """Raised when page fetching fails."""

class ExtractionError(ScraperError):
    """Raised when extraction fails."""

class ConfigGenerationError(ScraperError):
    """Raised when config generation fails."""
```

**Log errors with context:**
```python
try:
    result = await use_case.execute(request)
except ConfigGenerationError as e:
    logger.error(f"Config generation failed for {domain}/{page_type}: {e}")
    raise
```

## Key Development Workflows

### Adding a New Adapter

1. Create file in appropriate `adapters/` subdirectory
2. Implement the corresponding port interface
3. Keep implementation <150 lines
4. Add to DI Container (`config.py`)
5. Write unit tests with mocked dependencies
6. Write integration tests with real implementation
7. Update `.env.example` if new config needed

**Example:**
```python
# scraper/adapters/alerting/console_alerting.py
from scraper.ports.alerting import Alerting
from scraper.domain.models import AlertSeverity

class ConsoleAlerting(Alerting):
    """Simple console-based alerting for development."""

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        emoji = "ℹ️" if severity == AlertSeverity.INFO else "⚠️" if severity == AlertSeverity.WARNING else "🚨"
        print(f"{emoji} [{severity.value.upper()}] {title}")
        print(f"   {message}")
        if metadata:
            print(f"   Metadata: {metadata}")
```

### Adding a New Use Case

1. Create file in `use_cases/`
2. Define `__init__` with port dependencies
3. Implement `execute()` method
4. Write tests first (TDD)
5. Document with comprehensive docstring

### Implementing a New Page Type

1. Add enum value to `PageType` in `domain/models.py`
2. Create sample pages (3-5 URLs)
3. Define output schema (JSON Schema format)
4. Run config generation with samples
5. Test extraction on new pages
6. Monitor coverage statistics

### Debugging Extraction Issues

1. **Check config:** Is selector correct? Test in browser DevTools
2. **Check coverage:** Run `get_coverage_stats()` for the page type
3. **Check logs:** Enable debug logging to see extraction attempts
4. **Re-generate config:** If coverage <70%, regenerate with new samples
5. **Manual test:** Use `lxml_extractor` directly on sample HTML

## Working with Claude Code

### Expectations

When working on this codebase:

1. **ALWAYS FOLLOW TDD** - No production code without a failing test first
2. **Read docs first** - Understand System Design v2.0 before coding
3. **Ask clarifying questions** - Don't assume or guess
4. **Think from first principles** - Understand the "why" behind requirements
5. **Keep it simple** - YAGNI applies to everything
6. **Each adapter <150 lines** - If longer, split responsibilities

### Before Making Changes

1. Read relevant specification in `docs/`
2. Understand the full context
3. Review existing tests
4. Identify what tests need to be written
5. Write tests (RED)
6. Implement (GREEN)
7. Refactor if valuable
8. Update docs if needed

### When Stuck

1. Review System Design v2.0 for clarity
2. Check if there are related tests
3. Look for similar patterns in codebase
4. Ask specific questions with context
5. Propose 2-3 solutions with trade-offs

## Important Notes

### YAGNI (You Aren't Gonna Need It)

**Do not implement features not in specifications.**

If you think a feature is missing:
1. Document why you think it's needed
2. Propose specific use case
3. Wait for specification update
4. Then implement

### Cost Optimization is Critical

At 100 domains, 10k pages/month each:
- **v1.0 (page-level):** $18,000/year
- **v2.0 (field-level):** $2,820/year
- **Savings:** $15,180/year

Always prefer deterministic extraction over LLM. Only use LLM when necessary.

### Coverage Tracking is Key

Monitor field-level success rates:
- **>= 95%:** Excellent - No action needed
- **80-94%:** Good - Monitor closely
- **70-79%:** Warning - Schedule repair
- **< 70%:** Critical - Regenerate config immediately

### Multi-Sample Config Generation

Always use 3-5 sample pages when generating configs. Single-sample configs are brittle and fail in production.

### Field-Level Fallback

Never re-extract the entire page with LLM. Only extract missing fields. This is the key cost optimization.

## Quick Reference

### Common Tasks

```bash
# Start fresh
make clean && make setup

# Run tests
make test
make test-integration
make test-all

# Check code quality
make lint
make lint-fix
make format

# Development
make shell  # IPython with imports
make run    # Run CLI
```

### Key Files

- `/docs/SYSTEM_DESIGN_LLM_Web_Scraper_v2.0.md` - Complete technical spec
- `/docs/ParserGPT_Comparison.md` - Design rationale
- `/docs/QUICKSTART.md` - 5-minute setup guide
- `scraper/config.py` - DI Container
- `scraper/domain/models.py` - All domain models

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...    # For LLM operations

# Optional (defaults to simple adapters)
FETCHER=playwright              # or httpx
STORAGE=s3                      # or local
LLM_PROVIDER=pocketflow         # or direct
ALERTING=knock                  # or console

# S3 Storage (if used)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=...

# Knock Alerting (if used)
KNOCK_API_KEY=...
KNOCK_WORKFLOW_KEY=...
```

## Phase Roadmap

### Phase 1 (Weeks 1-4): Core System ✅
- Simple adapters (httpx, local, console)
- Basic LLM provider (single-sample config)
- Core use cases (ScrapePage)
- **Goal:** Working end-to-end

### Phase 2 (Weeks 5-8): ParserGPT Enhancements 🚧
- Multi-sample config generation
- Field-level LLM fallback
- Validation + repair loops
- Coverage tracking
- **Goal:** Production-quality extraction

### Phase 3 (Weeks 9-16): Scale 📋
- Production adapters (S3, Knock, Playwright)
- Orchestration (scheduling, queues)
- Advanced observability
- **Goal:** 100+ domains at scale

---

**Remember: Clean Architecture + YAGNI + TDD + ParserGPT Patterns = Production-Ready Web Scraper**

**Version:** 2.0
**Last Updated:** November 17, 2025
**Author:** Diego (CTO, Pickle)
