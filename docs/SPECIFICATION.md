# Feature Specification: LLM Web Scraper v2.0 - Core System

**Feature Branch**: `feature/phase-1-core-system`
**Created**: 2025-11-17
**Status**: Draft
**Version**: 2.0

## Table of Contents

1. [User Scenarios & Testing](#user-scenarios--testing-mandatory)
2. [Requirements](#requirements-mandatory)
3. [Key Entities](#key-entities)
4. [Success Criteria](#success-criteria-mandatory)
5. [Implementation Phases](#implementation-phases)
6. [Assumptions](#assumptions)
7. [Out of Scope](#out-of-scope)

---

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Basic Page Scraping with XPath Extraction (Priority: P1)

As a developer, I want to scrape a web page using pre-configured XPath selectors, so that I can extract structured data deterministically without using LLM for every page.

**Why this priority**: This is the core functionality that delivers 85% of extractions at zero LLM cost. Without this, the system has no cost advantage.

**Independent Test**: Can be fully tested by providing a URL and a config with XPath selectors, executing the scrape, and verifying extracted JSON matches expected output. Delivers immediate value of fast, cheap extraction.

**Acceptance Scenarios**:

1. **Given** a page config with XPath selectors exists, **When** user scrapes a URL, **Then** data is extracted using XPath and returned in JSON format
2. **Given** XPath extraction succeeds for all required fields, **When** extraction completes, **Then** no LLM calls are made and cost is $0
3. **Given** XPath extraction completes, **When** results are saved, **Then** both raw HTML and extracted JSON are stored with timestamps
4. **Given** multiple fields have XPath selectors, **When** extraction runs, **Then** all fields are attempted and results include success/failure status per field
5. **Given** a selector fails to match, **When** extraction completes, **Then** the missing field is identified in the `fields_missing` list

**Test Implementation**:
```python
# tests/unit/test_use_cases/test_scrape_page.py
async def test_scrape_page_with_xpath_only():
    """GIVEN config with XPath selectors, WHEN scraping page,
    THEN data extracted without LLM calls."""
```

---

### User Story 2 - Field-Level LLM Fallback (Priority: P1)

As a developer, I want missing fields to be extracted via LLM after XPath fails, so that I get complete data while minimizing LLM costs.

**Why this priority**: This is the key cost optimization (85% reduction). Core value proposition of the system.

**Independent Test**: Can be tested by providing a page where XPath extracts 8/10 fields, then verifying only the 2 missing fields are sent to LLM. Delivers value of cost-efficient completeness.

**Acceptance Scenarios**:

1. **Given** XPath extracted 9 of 10 required fields, **When** LLM fallback runs, **Then** only the 1 missing field is sent to LLM (not all 10)
2. **Given** LLM successfully extracts missing fields, **When** results are merged, **Then** XPath results are preferred over LLM results for overlapping fields
3. **Given** LLM fallback completes, **When** results are saved, **Then** the `llm_fields_used` list contains only fields that required LLM
4. **Given** both XPath and LLM fail for a required field, **When** extraction completes, **Then** extraction_method is set to FAILED and error is logged
5. **Given** field-level fallback is used, **When** 100 pages are scraped with 85% XPath success, **Then** total LLM cost is <$0.50 (vs $15 for page-level)

**Test Implementation**:
```python
# tests/unit/test_use_cases/test_extract_with_fallback.py
async def test_field_level_fallback_only_extracts_missing_fields():
    """GIVEN XPath extracted 9/10 fields, WHEN LLM fallback runs,
    THEN only missing field sent to LLM."""
```

---

### User Story 3 - Multi-Sample Config Generation (Priority: P2)

As a developer, I want to generate extraction configs from 3-5 sample pages, so that selectors work robustly across different page variations.

**Why this priority**: Enables automated config generation but basic scraping with manually-created configs already works. Critical for scale.

**Independent Test**: Can be tested by providing 5 sample URLs, generating config, and verifying selectors work on all 5 samples. Delivers value of automated config creation.

**Acceptance Scenarios**:

1. **Given** 5 sample URLs of the same page type, **When** config generation runs, **Then** LLM proposes XPath selectors that work across all samples
2. **Given** proposed selectors are tested on samples, **When** any selector fails on >20% of samples, **Then** repair loop is triggered
3. **Given** config generation completes, **When** final config is saved, **Then** coverage stats show >80% field extraction success
4. **Given** repair loop runs 3 times, **When** coverage is still <80%, **Then** warning is logged but config is saved anyway
5. **Given** multi-sample config exists, **When** applied to new pages of same type, **Then** extraction success rate is >85%

**Test Implementation**:
```python
# tests/unit/test_use_cases/test_generate_config.py
async def test_generate_config_with_multiple_samples():
    """GIVEN 5 sample pages, WHEN config generated,
    THEN selectors work on all samples."""
```

---

### User Story 4 - Coverage Tracking and Monitoring (Priority: P2)

As a developer, I want to track field-level extraction success rates over time, so that I can identify degrading selectors and regenerate configs proactively.

**Why this priority**: Enables proactive maintenance but basic scraping works without it. Important for production reliability.

**Independent Test**: Can be tested by scraping 100 pages, then querying coverage stats and verifying success rates match actual extractions. Delivers value of quality monitoring.

**Acceptance Scenarios**:

1. **Given** 100 pages have been scraped, **When** coverage stats are queried, **Then** each field shows success rate (e.g., name: 98%, email: 72%)
2. **Given** a field has <70% success rate, **When** stats are checked, **Then** alert is triggered to regenerate config
3. **Given** coverage stats are updated after each scrape, **When** stats are queried, **Then** results reflect most recent 1000 scrapes (rolling window)
4. **Given** multiple page types exist, **When** stats are queried, **Then** coverage is tracked separately per domain/page_type combination
5. **Given** field success rate improves after config regeneration, **When** stats are compared, **Then** improvement is measurable (e.g., 72% → 91%)

**Test Implementation**:
```python
# tests/unit/test_adapters/test_local_storage.py
async def test_coverage_stats_track_field_success_rates():
    """GIVEN multiple scrapes completed, WHEN stats queried,
    THEN success rates accurate per field."""
```

---

### User Story 5 - Configuration Validation and Repair (Priority: P3)

As a developer, I want configs to be validated against sample pages with automatic repair for failures, so that production configs have high quality before deployment.

**Why this priority**: Improves config quality but basic generation already works. Can be added as polish.

**Independent Test**: Can be tested by generating config with intentionally weak selectors, running validation, and verifying repair improves coverage. Delivers value of quality assurance.

**Acceptance Scenarios**:

1. **Given** initial selectors have 60% coverage on samples, **When** repair loop runs, **Then** coverage improves to >80%
2. **Given** repair loop identifies failing fields, **When** LLM repair is called, **Then** only failing selectors are modified (working ones preserved)
3. **Given** repair loop runs for 3 iterations, **When** coverage plateaus, **Then** loop terminates and best config is saved
4. **Given** validation identifies a selector that never works, **When** repair runs, **Then** completely new selector strategy is proposed
5. **Given** repaired config is saved, **When** metadata is checked, **Then** `total_pages_tested` and `last_validated` fields are populated

**Test Implementation**:
```python
# tests/unit/test_use_cases/test_generate_config.py
async def test_config_validation_and_repair_loop():
    """GIVEN low coverage config, WHEN repair runs,
    THEN coverage improves via targeted fixes."""
```

---

### Edge Cases

- What happens when a page has no HTML content (empty response)? → Return FAILED extraction with error message
- What happens when all XPath selectors fail but page loads successfully? → Trigger full-page LLM extraction as fallback
- How does the system handle pages that timeout during fetch? → Return FetchError, save error to logs, no extraction attempted
- What happens if LLM API is unavailable during field-level fallback? → Return partial results with `extraction_method=XPATH`, log missing fields
- What happens when a config doesn't exist for a domain/page_type combination? → Log warning, attempt LLM_DIRECT extraction, recommend config generation
- What happens if sample URLs provided for config generation are of different page types? → Detect structure mismatch, return error asking for consistent samples
- What happens when coverage stats file is corrupted? → Recreate stats file from scratch with warning logged
- How does the system handle concurrent scrapes to the same URL? → Each scrape is independent; no locking required
- What happens when required fields are missing from schema but present in config? → Log warning, include in extraction anyway (permissive approach)
- What happens if a selector extracts multiple values when single value expected? → Take first value, log warning about ambiguous selector

---

## Requirements _(mandatory)_

### Functional Requirements - Core Architecture

**FR-ARCH-001**: System MUST implement Clean Architecture with four distinct layers: Domain, Ports, Adapters, Use Cases

**FR-ARCH-002**: Domain layer MUST have zero dependencies on infrastructure (no imports from adapters, ports, or external libraries except Pydantic)

**FR-ARCH-003**: Use cases MUST depend only on Port interfaces, never on concrete Adapter implementations

**FR-ARCH-004**: Adapters MUST implement Port interfaces and remain under 150 lines of code each

**FR-ARCH-005**: System MUST support swapping adapters via environment variables without code changes

**FR-ARCH-006**: DI Container MUST resolve adapter instances based on `.env` configuration

**FR-ARCH-007**: All adapter implementations MUST be stateless and safe for concurrent use

### Functional Requirements - Page Fetching

**FR-FETCH-001**: System MUST provide PageFetcher port with async `fetch(url, timeout)` method

**FR-FETCH-002**: System MUST implement HttpxFetcher adapter for simple HTTP GET requests

**FR-FETCH-003**: HttpxFetcher MUST support configurable timeout (default 30 seconds)

**FR-FETCH-004**: HttpxFetcher MUST return raw HTML as string

**FR-FETCH-005**: HttpxFetcher MUST raise FetchError on HTTP errors (4xx, 5xx)

**FR-FETCH-006**: HttpxFetcher MUST raise FetchError on network timeouts

**FR-FETCH-007**: System MUST implement PlaywrightFetcher adapter for JavaScript-rendered pages (Phase 3)

**FR-FETCH-008**: Fetcher selection MUST be controlled via `FETCHER` environment variable

### Functional Requirements - XPath Extraction

**FR-XPATH-001**: System MUST provide Extractor port with `extract(html, config)` method

**FR-XPATH-002**: System MUST implement LxmlExtractor adapter using lxml library

**FR-XPATH-003**: LxmlExtractor MUST support XPath selectors from config

**FR-XPATH-004**: LxmlExtractor MUST support CSS selectors from config

**FR-XPATH-005**: LxmlExtractor MUST return ExtractionResult with data dict and metadata

**FR-XPATH-006**: ExtractionResult MUST include `fields_extracted` count and `fields_missing` list

**FR-XPATH-007**: ExtractionResult MUST include `attempted_selectors` mapping field names to selectors used

**FR-XPATH-008**: LxmlExtractor MUST handle multiple value extraction when `multiple: true` in config

**FR-XPATH-009**: LxmlExtractor MUST handle extraction errors gracefully and continue with other fields

**FR-XPATH-010**: LxmlExtractor MUST set `extraction_method` to XPATH when all fields extracted successfully

### Functional Requirements - LLM Integration

**FR-LLM-001**: System MUST provide LLMProvider port with three methods: `propose_selectors`, `repair_selectors`, `extract_fields`

**FR-LLM-002**: System MUST implement DirectProvider adapter for Anthropic/OpenAI APIs

**FR-LLM-003**: DirectProvider MUST support Anthropic API via `anthropic` library

**FR-LLM-004**: DirectProvider MUST support OpenAI API via `openai` library (future)

**FR-LLM-005**: DirectProvider MUST use structured output (Pydantic models) for all LLM responses

**FR-LLM-006**: `propose_selectors()` MUST accept 3-5 PageSample objects and return PageTypeConfig

**FR-LLM-007**: `repair_selectors()` MUST accept current config and failures list, return improved config

**FR-LLM-008**: `extract_fields()` MUST accept HTML and list of field names, return only requested fields

**FR-LLM-009**: `extract_fields()` MUST truncate HTML to 12,000 characters before sending to LLM

**FR-LLM-010**: DirectProvider MUST use temperature=0.1 for all operations (deterministic)

**FR-LLM-011**: DirectProvider MUST implement retry logic (max 3 retries) for API failures

**FR-LLM-012**: LLM provider selection MUST be controlled via `LLM_PROVIDER` environment variable

### Functional Requirements - Field-Level Fallback

**FR-FALLBACK-001**: ExtractWithFallback use case MUST attempt XPath extraction first

**FR-FALLBACK-002**: ExtractWithFallback MUST identify missing required fields after XPath

**FR-FALLBACK-003**: ExtractWithFallback MUST call `llm.extract_fields()` with ONLY missing fields

**FR-FALLBACK-004**: ExtractWithFallback MUST merge XPath and LLM results, preferring XPath values

**FR-FALLBACK-005**: ExtractWithFallback MUST set `extraction_method` to XPATH_WITH_LLM_FALLBACK when both used

**FR-FALLBACK-006**: ExtractWithFallback MUST populate `llm_fields_used` list with field names extracted by LLM

**FR-FALLBACK-007**: ExtractWithFallback MUST NOT extract optional fields with LLM (only required fields)

**FR-FALLBACK-008**: ExtractWithFallback MUST update coverage statistics after each extraction

**FR-FALLBACK-009**: ExtractWithFallback MUST handle LLM errors gracefully and return partial results

### Functional Requirements - Config Generation

**FR-CONFIG-001**: GenerateConfig use case MUST accept 3-5 sample URLs

**FR-CONFIG-002**: GenerateConfig MUST fetch HTML for each sample URL

**FR-CONFIG-003**: GenerateConfig MUST call `llm.propose_selectors()` with all samples

**FR-CONFIG-004**: GenerateConfig MUST validate proposed selectors against all samples

**FR-CONFIG-005**: GenerateConfig MUST calculate coverage as (successful_fields / total_fields) across all samples

**FR-CONFIG-006**: GenerateConfig MUST trigger repair loop when coverage < 80%

**FR-CONFIG-007**: GenerateConfig MUST run maximum 3 repair iterations

**FR-CONFIG-008**: GenerateConfig MUST identify specific field failures for targeted repair

**FR-CONFIG-009**: GenerateConfig MUST save config with coverage_stats, last_validated, and total_pages_tested metadata

**FR-CONFIG-010**: GenerateConfig MUST return ConfigGenerationResult with final_coverage and iterations_needed

**FR-CONFIG-011**: GenerateConfig MUST send alert when final coverage < 80% after max iterations

### Functional Requirements - Storage

**FR-STORAGE-001**: System MUST provide Storage port with config, HTML, JSON, and coverage methods

**FR-STORAGE-002**: System MUST implement LocalStorage adapter using filesystem

**FR-STORAGE-003**: LocalStorage MUST save configs to `data/configs/{domain}/{page_type}.json`

**FR-STORAGE-004**: LocalStorage MUST save HTML to `data/html/{domain}/{timestamp}_{url_hash}.html`

**FR-STORAGE-005**: LocalStorage MUST save JSON to `data/json/{domain}/{timestamp}_{url_hash}.json`

**FR-STORAGE-006**: LocalStorage MUST save coverage stats to `data/coverage-stats/{domain}/{page_type}.json`

**FR-STORAGE-007**: Coverage stats file MUST track per-field success/total counts

**FR-STORAGE-008**: `update_coverage_stats()` MUST increment field counters atomically

**FR-STORAGE-009**: `get_coverage_stats()` MUST return success rates as floats (0.0 to 1.0)

**FR-STORAGE-010**: Storage selection MUST be controlled via `STORAGE` environment variable

**FR-STORAGE-011**: LocalStorage MUST create directories automatically if they don't exist

**FR-STORAGE-012**: All file operations MUST include error handling for I/O failures

### Functional Requirements - Alerting

**FR-ALERT-001**: System MUST provide Alerting port with `send_alert()` method

**FR-ALERT-002**: System MUST implement ConsoleAlerting adapter for development

**FR-ALERT-003**: ConsoleAlerting MUST print alerts to stdout with severity emoji

**FR-ALERT-004**: Alerts MUST include title, message, severity, and optional metadata

**FR-ALERT-005**: Severity levels MUST be: INFO, WARNING, CRITICAL

**FR-ALERT-006**: ConsoleAlerting MUST use ℹ️ for INFO, ⚠️ for WARNING, 🚨 for CRITICAL

**FR-ALERT-007**: Alerting selection MUST be controlled via `ALERTING` environment variable

### Functional Requirements - End-to-End Scraping

**FR-E2E-001**: ScrapePage use case MUST orchestrate fetch → extract → save workflow

**FR-E2E-002**: ScrapePage MUST load existing config or return error if none exists

**FR-E2E-003**: ScrapePage MUST use ExtractWithFallback for extraction with field-level fallback

**FR-E2E-004**: ScrapePage MUST save both HTML and JSON after successful extraction

**FR-E2E-005**: ScrapePage MUST update coverage stats after each scrape

**FR-E2E-006**: ScrapePage MUST return ScrapeResult with all metadata (url, timestamp, paths, success)

**FR-E2E-007**: ScrapePage MUST handle FetchError by returning failed ScrapeResult with error message

**FR-E2E-008**: ScrapePage MUST handle missing config by attempting LLM_DIRECT extraction (future)

### Functional Requirements - Domain Models

**FR-MODEL-001**: System MUST define PageSample model with url, html, fetched_at fields

**FR-MODEL-002**: System MUST define FieldFailure model for targeted repair

**FR-MODEL-003**: System MUST define ExtractionResult model with data, method, confidence, fields info

**FR-MODEL-004**: System MUST define PageTypeConfig model with selectors, schema, coverage stats

**FR-MODEL-005**: System MUST define ConfigGenerationResult model with config and generation metadata

**FR-MODEL-006**: System MUST define ExtractionMethod enum with XPATH, XPATH_WITH_LLM_FALLBACK, LLM_FALLBACK, LLM_DIRECT, FAILED

**FR-MODEL-007**: System MUST define PageType enum with TEAM_PAGE, CAREERS_PAGE, PROVIDER_DIRECTORY, LICENSE_DIRECTORY, UNKNOWN

**FR-MODEL-008**: System MUST define AlertSeverity enum with INFO, WARNING, CRITICAL

**FR-MODEL-009**: All models MUST be Pydantic BaseModels with validation

**FR-MODEL-010**: All models MUST use type hints for all fields

### Functional Requirements - CLI

**FR-CLI-001**: System MUST provide `scraper` CLI command via entry point

**FR-CLI-002**: CLI MUST support `scraper scrape <url> --domain <domain> --page-type <type>` command

**FR-CLI-003**: CLI MUST support `scraper generate-config --domain <domain> --page-type <type> --samples <urls>` command

**FR-CLI-004**: CLI MUST support `scraper coverage --domain <domain> --page-type <type>` command

**FR-CLI-005**: CLI MUST load environment variables from `.env` file

**FR-CLI-006**: CLI MUST print results in human-readable format

**FR-CLI-007**: CLI MUST exit with code 0 on success, non-zero on failure

---

## Key Entities

### PageSample
Represents a sample web page used for config generation.
- **Properties**: url (HttpUrl), html (str), fetched_at (datetime)
- **Used by**: GenerateConfig use case, LLMProvider
- **Lifecycle**: Created during sample collection, passed to LLM for analysis, discarded after config generation

### FieldFailure
Represents a field that failed extraction during validation.
- **Properties**: field_name (str), sample_url (HttpUrl), html_snippet (str), current_selector (Optional[str])
- **Used by**: GenerateConfig for repair loop
- **Lifecycle**: Created when validation detects failure, passed to LLM for repair, discarded after repair completes

### ExtractionResult
Represents the output of a single extraction attempt.
- **Properties**: data (Dict[str, Any]), extraction_method (ExtractionMethod), confidence (float), fields_extracted (int), fields_missing (List[str]), llm_fields_used (List[str]), attempted_selectors (Dict[str, str])
- **Used by**: All extraction flows (XPath, LLM, fallback)
- **Lifecycle**: Created by Extractor or merged from XPath+LLM, returned to use case, used to update coverage stats

### PageTypeConfig
Represents extraction configuration for a specific domain and page type.
- **Properties**: version (str), domain (str), page_type (PageType), selectors (Dict[str, Dict[str, Any]]), schema (Dict[str, Any]), coverage_stats (Dict[str, float]), last_validated (Optional[datetime]), total_pages_tested (int)
- **Used by**: All use cases that perform extraction
- **Lifecycle**: Generated once, saved to storage, loaded for each scrape, updated with coverage stats, regenerated when coverage degrades

### ConfigGenerationResult
Represents the outcome of config generation process.
- **Properties**: config (PageTypeConfig), final_coverage (float), iterations_needed (int), config_path (str), sample_count (int)
- **Used by**: GenerateConfig use case
- **Lifecycle**: Created at end of generation process, returned to caller, logged for monitoring

### ScrapeResult
Represents the complete outcome of scraping a single page.
- **Properties**: url (str), domain (str), page_type (PageType), extraction_method (ExtractionMethod), html_path (str), json_path (str), timestamp (datetime), data (Dict[str, Any]), success (bool), error_message (Optional[str])
- **Used by**: ScrapePage use case
- **Lifecycle**: Created after scrape completes (success or failure), returned to CLI, logged for monitoring

---

## Success Criteria _(mandatory)_

### Measurable Outcomes - Performance

**SC-PERF-001**: XPath extraction MUST complete in <500ms for pages with <100KB HTML

**SC-PERF-002**: Field-level LLM fallback (1-3 fields) MUST complete in <3 seconds

**SC-PERF-003**: Full config generation (5 samples, 3 iterations) MUST complete in <2 minutes

**SC-PERF-004**: System MUST support scraping 100 pages in <5 minutes with 85% XPath success (mostly parallel)

**SC-PERF-005**: Storage operations (save HTML, JSON, config) MUST complete in <100ms each

### Measurable Outcomes - Cost Efficiency

**SC-COST-001**: XPath-only extraction MUST cost $0 (no LLM usage)

**SC-COST-002**: Field-level fallback (extracting 2 missing fields from 10-field page) MUST cost <$0.01

**SC-COST-003**: Scraping 1000 pages with 85% XPath success MUST cost <$5 total

**SC-COST-004**: Config generation (5 samples, 2 iterations) MUST cost <$0.15 total

**SC-COST-005**: System MUST achieve >80% cost reduction vs page-level LLM fallback

### Measurable Outcomes - Accuracy

**SC-ACC-001**: XPath extraction MUST achieve >85% success rate on production pages (when config is well-tuned)

**SC-ACC-002**: Field-level LLM fallback MUST extract missing required fields with >90% accuracy

**SC-ACC-003**: Multi-sample config generation MUST produce selectors that work on >80% of validation samples

**SC-ACC-004**: Config repair loop MUST improve coverage by >10 percentage points per iteration (when possible)

**SC-ACC-005**: Coverage tracking MUST accurately reflect success rates within ±2% margin

### Measurable Outcomes - Reliability

**SC-REL-001**: System MUST handle network failures gracefully (no crashes, proper error messages)

**SC-REL-002**: System MUST handle malformed HTML gracefully (lxml parsing errors don't crash system)

**SC-REL-003**: System MUST handle LLM API failures with automatic retry (3 attempts)

**SC-REL-004**: System MUST maintain data consistency (HTML and JSON always saved together or not at all)

**SC-REL-005**: System MUST support concurrent scrapes without data corruption

### Measurable Outcomes - Usability

**SC-USE-001**: Developer MUST be able to scrape a page with existing config in <30 seconds (including CLI invocation)

**SC-USE-002**: Developer MUST be able to generate new config from 5 samples in <3 minutes (including sample collection)

**SC-USE-003**: Developer MUST be able to check coverage stats in <10 seconds via CLI

**SC-USE-004**: Error messages MUST include actionable information (what failed, why, how to fix)

**SC-USE-005**: All CLI commands MUST provide help text via `--help` flag

### Measurable Outcomes - Testability

**SC-TEST-001**: All use cases MUST be testable with mocked ports (unit tests run in <1 second total)

**SC-TEST-002**: All adapters MUST be testable in isolation (adapter tests run in <5 seconds total)

**SC-TEST-003**: System MUST achieve >80% code coverage for domain and use case layers

**SC-TEST-004**: Integration tests with real adapters MUST run in <30 seconds

**SC-TEST-005**: End-to-end test (generate config → scrape → verify) MUST run in <2 minutes

---

## Implementation Phases

### Phase 1: Core System (Weeks 1-4) - CURRENT PRIORITY

**Week 1: Simple Adapters**
- [ ] Implement ConsoleAlerting adapter (~30 lines)
- [ ] Implement LocalStorage adapter with config/HTML/JSON methods (~100 lines)
- [ ] Implement HttpxFetcher adapter (~40 lines)
- [ ] Unit tests for all adapters with mocked dependencies
- [ ] Integration tests for LocalStorage (real filesystem)

**Week 2: LLM + Extraction**
- [ ] Implement DirectProvider adapter with extract_fields() only (~80 lines)
- [ ] Implement LxmlExtractor adapter (~120 lines)
- [ ] Unit tests for LLM and extractor
- [ ] Integration test with real Anthropic API (small prompt)

**Week 3: Basic Use Cases**
- [ ] Implement ExtractWithFallback use case (~100 lines)
- [ ] Implement ScrapePage use case (~80 lines)
- [ ] Complete DI Container in config.py (~60 lines)
- [ ] Unit tests for all use cases
- [ ] Integration test for full scraping workflow

**Week 4: CLI + Integration**
- [ ] Implement CLI with scrape command (~100 lines)
- [ ] Add logging configuration
- [ ] End-to-end test: scrape real page with manual config
- [ ] Documentation: how to create manual configs
- [ ] **Milestone: First successful scrape!**

### Phase 2: ParserGPT Enhancements (Weeks 5-8)

**Week 5: Multi-Sample Config Generation**
- [ ] Enhance DirectProvider with propose_selectors()
- [ ] Implement sample collection in GenerateConfig
- [ ] Basic validation loop (no repair yet)
- [ ] CLI: `generate-config` command
- [ ] Test: generate config from 5 samples

**Week 6: Field-Level Fallback (Enhanced)**
- [ ] Already implemented in Phase 1, but add metrics
- [ ] Track LLM usage per field
- [ ] Cost tracking and reporting
- [ ] Test: verify cost reduction vs page-level

**Week 7: Validation + Repair**
- [ ] Implement repair_selectors() in DirectProvider
- [ ] Implement repair loop in GenerateConfig (max 3 iterations)
- [ ] Coverage calculation and quality gates
- [ ] Test: repair improves low-quality configs

**Week 8: Coverage Tracking**
- [ ] Implement coverage stats in LocalStorage
- [ ] Add update_coverage_stats() calls to ExtractWithFallback
- [ ] CLI: `coverage` command to view stats
- [ ] Alerting for low coverage fields
- [ ] Test: stats accurately reflect extractions

### Phase 3: Production Scale (Weeks 9-16)

**Week 9-10: Production Adapters**
- [ ] Implement S3Storage adapter with coverage tracking
- [ ] Implement KnockAlerting adapter
- [ ] Implement PlaywrightFetcher adapter
- [ ] Configuration for production environment

**Week 11-12: Orchestration**
- [ ] Job scheduling framework
- [ ] Retry logic and error handling
- [ ] Rate limiting for LLM APIs
- [ ] Batch processing

**Week 13-14: Advanced Features**
- [ ] PocketFlowProvider for LLM orchestration
- [ ] Auto-config regeneration based on coverage
- [ ] A/B testing for selector strategies

**Week 15-16: Observability**
- [ ] Prometheus metrics export
- [ ] Structured logging
- [ ] Cost tracking dashboard
- [ ] Performance monitoring

---

## Assumptions

### Technical Assumptions

- Python 3.12+ is available in deployment environment
- `uv` package manager is used for dependency management
- Anthropic API key is available for LLM operations
- Developers have basic understanding of XPath/CSS selectors
- HTML pages follow standard web conventions (valid markup, reasonable size <5MB)

### Architectural Assumptions

- Clean Architecture pattern is enforced via code review (no automated enforcement)
- Adapters remain under 150 lines through careful design and refactoring
- DI Container pattern is sufficient for adapter selection (no complex DI framework needed)
- Environment variables are the preferred configuration mechanism
- Pytest is the testing framework for all test types

### Operational Assumptions

- Config generation is a manual/semi-automated process (not fully automated pipeline in Phase 1)
- Developers manually select sample URLs for config generation
- Coverage monitoring is manual in Phase 1 (automated alerts in Phase 2)
- Single deployment instance (no distributed system concerns in Phase 1)
- Local filesystem storage is acceptable for Phase 1 (S3 in Phase 3)

### Business Assumptions

- Cost optimization (85% reduction) is more valuable than 100% extraction accuracy
- It's acceptable to miss optional fields if it saves LLM cost
- Config regeneration frequency is low (monthly or when coverage degrades)
- Primary use case is scraping healthcare provider data (team pages, license directories)
- Scale target is 100 domains × 10K pages/month = 1M pages/month total

---

## Out of Scope

### Phase 1 Out of Scope (May be added in Phase 2-3)

- Real-time scraping (all operations are asynchronous batch jobs)
- Distributed scraping across multiple workers
- Scraping websites that require authentication/login
- JavaScript execution (Playwright adapter comes in Phase 3)
- Custom scraping rules beyond XPath/CSS selectors (e.g., complex regex, custom parsers)
- Pagination handling (each page scraped independently)
- Rate limiting or politeness delays (assumed handled by orchestration layer)
- Data deduplication (assumed handled by downstream systems)
- Schema evolution (configs are versioned but not automatically migrated)
- Multi-language support (all prompts and docs in English)

### Permanently Out of Scope

- Visual scraping (screenshot analysis, OCR)
- CAPTCHA solving
- Proxy rotation or IP management
- Browser fingerprinting or anti-bot evasion
- Data validation beyond basic type checking
- Entity resolution or data matching
- Data transformation beyond extraction (ETL is downstream)
- API scraping (this is for HTML scraping only)
- Real-time notifications when new data appears
- Data retention policies or automatic cleanup
- User authentication or access control (system-level tool)
- Multi-tenancy (single team/organization deployment)

---

## Test-Driven Development Approach

Every requirement MUST be implemented following Red-Green-Refactor:

### RED Phase: Write Failing Test
```python
# Example: tests/unit/test_use_cases/test_extract_with_fallback.py
async def test_field_level_fallback_only_extracts_missing_fields():
    """Test FR-FALLBACK-003: Only missing fields sent to LLM."""
    # Arrange: Mock adapters
    extractor = Mock(Extractor)
    llm = Mock(LLMProvider)
    storage = Mock(Storage)
    alerting = Mock(Alerting)

    # XPath extracts 9/10 fields (missing: email)
    xpath_result = ExtractionResult(
        data={"name": "John", "title": "CTO", "phone": "555-1234"},
        extraction_method=ExtractionMethod.XPATH,
        fields_missing=["email"]
    )
    extractor.extract.return_value = xpath_result

    # LLM extracts just the email
    llm.extract_fields.return_value = {"email": "john@example.com"}

    use_case = ExtractWithFallback(extractor, llm, storage, alerting)

    # Act: Execute extraction
    result = await use_case.execute(
        url="https://example.com/team",
        domain="example.com",
        page_type=PageType.TEAM_PAGE,
        html="<html>...</html>",
        config=mock_config
    )

    # Assert: Only missing field sent to LLM
    llm.extract_fields.assert_called_once()
    call_args = llm.extract_fields.call_args
    assert call_args.kwargs["fields_to_extract"] == ["email"]
    assert result.data["email"] == "john@example.com"
    assert result.llm_fields_used == ["email"]
```

### GREEN Phase: Implement Minimal Code
```python
# scraper/use_cases/extract_with_fallback.py
class ExtractWithFallback:
    def __init__(self, extractor, llm, storage, alerting):
        self.extractor = extractor
        self.llm = llm
        self.storage = storage
        self.alerting = alerting

    async def execute(self, url, domain, page_type, html, config):
        # Try XPath first
        xpath_result = self.extractor.extract(html, config)

        # Identify missing fields
        missing = xpath_result.fields_missing

        if not missing:
            return xpath_result

        # LLM fallback for ONLY missing fields
        llm_data = await self.llm.extract_fields(
            html=html,
            fields_to_extract=missing,
            schema={"properties": {f: config.schema["properties"][f] for f in missing}}
        )

        # Merge results
        merged = xpath_result.data.copy()
        merged.update(llm_data)

        return ExtractionResult(
            data=merged,
            extraction_method=ExtractionMethod.XPATH_WITH_LLM_FALLBACK,
            llm_fields_used=missing
        )
```

### REFACTOR Phase: Improve While Tests Pass
- Extract helper methods if logic gets complex
- Add type hints if missing
- Improve variable names
- Remove duplication
- Tests must still pass!

---

## Appendix: Requirements Traceability Matrix

| Requirement ID | User Story | Test File | Implementation File |
|---------------|-----------|-----------|-------------------|
| FR-FALLBACK-003 | US-2 | test_extract_with_fallback.py | extract_with_fallback.py |
| FR-CONFIG-006 | US-3 | test_generate_config.py | generate_config.py |
| FR-STORAGE-007 | US-4 | test_local_storage.py | local_storage.py |
| FR-XPATH-006 | US-1 | test_lxml_extractor.py | lxml_extractor.py |
| ... | ... | ... | ... |

*(Full matrix to be maintained as implementation progresses)*

---

**Document Version**: 1.0
**Last Updated**: November 17, 2025
**Next Review**: End of Phase 1 (Week 4)
**Author**: Diego
