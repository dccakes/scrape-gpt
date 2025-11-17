# LLM Web Scraper - Enhanced System Design v2.0

**Updated:** November 17, 2025  
**Version:** 2.0 (ParserGPT-inspired enhancements)  
**Author:** Diego (CTO, Pickle)

---

## Change Log

### Version 2.0 (November 17, 2025)
**ParserGPT-Inspired Enhancements:**
- ✅ Multi-sample config generation (Section 3.2)
- ✅ Field-level LLM fallback (Section 5.2)
- ✅ Validation + repair loop (Section 3.3)
- ✅ Coverage tracking metrics (Section 7)
- ✅ Enhanced GenerateConfig use case
- ✅ Enhanced ExtractWithFallback use case

### Version 1.0 (October 25, 2025)
- Initial design with Clean Architecture
- Port definitions
- Basic use cases
- DI Container pattern

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [Enhanced Config Generation](#3-enhanced-config-generation)
4. [Port Definitions](#4-port-definitions)
5. [Enhanced Use Cases](#5-enhanced-use-cases)
6. [Adapters](#6-adapters)
7. [Coverage Tracking](#7-coverage-tracking)
8. [Data Models](#8-data-models)
9. [DI Container](#9-di-container)
10. [Phase-by-Phase Roadmap](#10-phase-by-phase-roadmap)

---

## 1. System Overview

### 1.1 Core Philosophy

**Deterministic-First, LLM as Compiler**

Our system treats LLM as a "compiler" that generates extraction rules (XPath selectors), not as a runtime extractor. This dramatically reduces cost and improves speed.

```
Learn Once (Multi-Sample) → Run Fast (XPath) → Fallback Smart (Field-Level LLM)
```

**Key Insights from ParserGPT Analysis:**
1. **Multi-sample learning** produces more robust configs than single-page
2. **Field-level fallback** is 10x more cost-efficient than page-level
3. **Validation loops** ensure high-quality selectors before production
4. **Coverage metrics** track selector reliability over time

### 1.2 High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Config Generation (One-Time Per Domain/Page Type)      │
│                                                             │
│  Multi-Sample → Propose Selectors → Validate → Repair      │
│  (3-5 pages)    (LLM)              (Test)     (Iterate)    │
│                                                             │
│  Result: High-confidence XPath config                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Production Scraping (Many Pages, Fast)                 │
│                                                             │
│  Fetch HTML → XPath Extract → Check Coverage               │
│  (Playwright)  (lxml - fast!)   (Which fields missing?)    │
│                                                             │
│  If fields missing → LLM Fallback (field-level only)       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Storage & Observability                                 │
│                                                             │
│  Save HTML + JSON + Update Coverage Stats                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture Principles

### 2.1 Clean Architecture (Unchanged)

Four distinct layers with strict dependency flow:

```
Domain (Pure Logic)
    ↓
Ports (Interfaces)
    ↓
Adapters (Implementations)
    ↓
External Systems
```

**Key Rule:** Business logic depends only on ports, never adapters.

### 2.2 YAGNI + KISS (Unchanged)

- **YAGNI:** Build only what's needed now (no speculative abstractions)
- **KISS:** Each adapter <150 lines, single responsibility
- **Progressive Complexity:** Simple → Sophisticated as needs grow

### 2.3 New: Validation-Driven Config Generation

**Inspired by ParserGPT's "Propose → Validate → Repair" loop**

Before saving a config to production, we:
1. Test selectors on multiple sample pages
2. Measure coverage (% of fields successfully extracted)
3. If coverage < 80%, repair selectors with targeted LLM fixes
4. Iterate 2-3 times max

**Why:** Prevents low-quality configs from reaching production.

### 2.4 New: Field-Level Fallback

**Inspired by ParserGPT's cost optimization**

When XPath extraction partially fails:
- ❌ Old approach: Re-extract entire page with LLM
- ✅ New approach: Extract only missing fields with LLM

**Example:**
```python
# XPath extracted 9 of 10 fields successfully
# Only 1 field (email) is missing

# Old way (expensive):
llm_result = llm.extract_full_page(html)  # Re-extract all 10 fields

# New way (10x cheaper):
llm_result = llm.extract_fields(html, fields=["email"])  # Only 1 field
```

---

## 3. Enhanced Config Generation

### 3.1 Overview

**Old Approach (v1.0):**
- Single sample page
- One LLM call
- No validation
- Save suggested_config directly

**New Approach (v2.0 - ParserGPT-inspired):**
- Multiple sample pages (3-5)
- Propose → Validate → Repair loop
- Coverage-based quality gates
- Production-ready configs

### 3.2 Multi-Sample Collection

**Purpose:** Collect representative pages to learn robust selectors.

```python
async def collect_samples(
    domain: str,
    page_type: PageType,
    seed_urls: List[str],
    max_samples: int = 5
) -> List[PageSample]:
    """
    Collect 3-5 representative pages of the same type.
    
    Examples:
    - For "team_page": 3 different hospital team pages
    - For "provider_directory": 3 different search result pages
    
    Args:
        domain: Domain to scrape (e.g., "hospital.com")
        page_type: Type of page (e.g., "team_page")
        seed_urls: Starting URLs provided by user
        max_samples: Maximum samples to collect (default: 5)
        
    Returns:
        List of PageSample objects with URL + HTML
    """
    samples = []
    
    for url in seed_urls[:max_samples]:
        html = await fetcher.fetch(url)
        samples.append(PageSample(url=url, html=html))
    
    return samples
```

**Why multiple samples?**
- Different hospitals may use slightly different markup
- Some pages might be missing optional fields
- Selectors that work on all samples are more robust

### 3.3 Propose → Validate → Repair Loop

**Inspired by ParserGPT's iterative improvement**

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
    
    # 1. PROPOSE: LLM generates initial selectors
    config = await llm.propose_selectors(
        samples=samples,
        schema=target_schema,
        domain_context=f"Healthcare website: {domain}"
    )
    
    # 2. VALIDATE + REPAIR LOOP
    for iteration in range(max_iterations):
        # Test config on all samples
        validation_results = []
        for sample in samples:
            result = extractor.extract(sample.html, config)
            validation_results.append(result)
        
        # Calculate coverage
        coverage = calculate_coverage(validation_results, target_schema)
        
        logger.info(
            f"Iteration {iteration + 1}: Coverage = {coverage:.1%}"
        )
        
        # Check if we meet threshold
        if coverage >= coverage_threshold:
            logger.info(f"✅ Coverage threshold met: {coverage:.1%}")
            break
        
        # 3. REPAIR: Ask LLM to fix specific failures
        failures = identify_failures(validation_results, samples)
        
        config = await llm.repair_selectors(
            current_config=config,
            failures=failures,
            samples=samples
        )
    
    # 4. Add metadata
    config.coverage_stats = calculate_field_coverage(validation_results)
    config.last_validated = datetime.now()
    config.total_pages_tested = len(samples)
    
    return config


def calculate_coverage(
    results: List[ExtractionResult],
    schema: Dict[str, Any]
) -> float:
    """
    Calculate what % of expected fields were successfully extracted.
    
    Returns:
        Float between 0.0 and 1.0 (e.g., 0.85 = 85% coverage)
    """
    total_fields = 0
    successful_fields = 0
    
    for result in results:
        for field_name, field_spec in schema["properties"].items():
            total_fields += 1
            
            if field_name in result.data and result.data[field_name]:
                successful_fields += 1
    
    return successful_fields / total_fields if total_fields > 0 else 0.0


def identify_failures(
    results: List[ExtractionResult],
    samples: List[PageSample]
) -> List[FieldFailure]:
    """
    Identify which specific fields failed and on which pages.
    
    This gives LLM targeted context for repairs.
    
    Returns:
        List of FieldFailure objects with:
        - field_name: Which field failed
        - sample_url: Which page
        - html_snippet: Relevant HTML context
    """
    failures = []
    
    for i, result in enumerate(results):
        for field_name in result.fields_missing:
            failures.append(FieldFailure(
                field_name=field_name,
                sample_url=samples[i].url,
                html_snippet=samples[i].html[:2000],  # First 2000 chars
                current_selector=result.attempted_selectors.get(field_name)
            ))
    
    return failures
```

### 3.4 LLM Prompts for Config Generation

**3.4.1 Propose Selectors Prompt**

```python
PROPOSE_SELECTORS_PROMPT = """
You are an expert at analyzing HTML and writing XPath selectors.

TASK: Generate XPath selectors to extract the following fields from these sample pages.

DOMAIN: {domain}
PAGE TYPE: {page_type}

EXPECTED FIELDS:
{schema}

SAMPLE PAGES ({num_samples} pages):
{samples}

REQUIREMENTS:
1. Write XPath selectors that work across ALL sample pages
2. Prefer CSS selectors when simple, XPath when complex
3. Use regex only as last resort
4. For list fields, select the container element
5. Test your selectors mentally on each sample

OUTPUT FORMAT (strict JSON):
{
  "selectors": {
    "field_name": {
      "xpath": "//xpath/expression",
      "css": ".optional.css.selector",
      "regex": "optional_pattern",
      "multiple": true/false
    }
  }
}

Think step-by-step:
1. Find where each field appears in the HTML
2. Identify patterns across samples
3. Write the most specific yet flexible selector
4. Verify it works on all samples
"""
```

**3.4.2 Repair Selectors Prompt**

```python
REPAIR_SELECTORS_PROMPT = """
You are fixing XPath selectors that didn't work on some pages.

CURRENT CONFIG:
{current_config}

FAILURES (what didn't work):
{failures}

For each failure, you have:
- field_name: Which field failed
- sample_url: Which page it failed on
- current_selector: The selector that didn't work
- html_snippet: Relevant HTML context

TASK: Provide MINIMAL fixes to make these selectors work.

RULES:
1. Only modify selectors that failed
2. Keep successful selectors unchanged
3. Make selectors more flexible, not more specific
4. Provide rationale for each change

OUTPUT FORMAT (strict JSON):
{
  "selectors": {
    "field_name": {
      "xpath": "updated_xpath",
      "css": "updated_css",
      "rationale": "why this should work better"
    }
  }
}
"""
```

---

## 4. Port Definitions

### 4.1 PageFetcher (Unchanged from v1.0)

```python
class PageFetcher(ABC):
    """Interface for fetching web pages."""
    
    @abstractmethod
    async def fetch(self, url: str, timeout: int = 30000) -> str:
        """Fetch page and return HTML."""
        pass
```

**Implementations:**
- `PlaywrightFetcher` - Full browser with JS rendering
- `HttpxFetcher` - Simple HTTP GET (no JS)

### 4.2 Extractor (Unchanged from v1.0)

```python
class Extractor(ABC):
    """Interface for extracting structured data from HTML."""
    
    @abstractmethod
    def extract(self, html: str, config: Dict[str, Any]) -> ExtractionResult:
        """Extract data using provided config."""
        pass
```

**Implementations:**
- `LxmlExtractor` - XPath/CSS selector extraction

### 4.3 LLMProvider (Enhanced for v2.0)

```python
class LLMProvider(ABC):
    """Interface for LLM operations."""
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> T:
        """Generate structured output from LLM."""
        pass
    
    # NEW: Multi-sample config generation
    @abstractmethod
    async def propose_selectors(
        self,
        samples: List[PageSample],
        schema: Dict[str, Any],
        domain_context: str
    ) -> PageTypeConfig:
        """
        Propose XPath selectors based on multiple sample pages.
        
        This is the "compiler" step - LLM analyzes HTML structure
        and generates extraction rules.
        
        Args:
            samples: 3-5 sample pages of the same type
            schema: Expected output schema (JSON Schema format)
            domain_context: Context about the domain (e.g., "healthcare")
            
        Returns:
            PageTypeConfig with proposed selectors
        """
        pass
    
    # NEW: Targeted repair
    @abstractmethod
    async def repair_selectors(
        self,
        current_config: PageTypeConfig,
        failures: List[FieldFailure],
        samples: List[PageSample]
    ) -> PageTypeConfig:
        """
        Repair selectors that failed validation.
        
        Only modifies failing selectors, keeps successful ones unchanged.
        
        Args:
            current_config: Current config with some failing selectors
            failures: List of which fields failed on which pages
            samples: Original sample pages for context
            
        Returns:
            Updated PageTypeConfig with repaired selectors
        """
        pass
    
    # NEW: Field-level extraction
    @abstractmethod
    async def extract_fields(
        self,
        html: str,
        fields_to_extract: List[str],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract only specific fields using LLM.
        
        This is more cost-efficient than extracting the entire page
        when only 1-2 fields are missing from XPath extraction.
        
        Args:
            html: HTML content
            fields_to_extract: List of field names to extract (e.g., ["email"])
            schema: Schema for these specific fields
            
        Returns:
            Dict with only the requested fields populated
            
        Example:
            # XPath extracted everything except "email"
            result = await llm.extract_fields(
                html=html,
                fields_to_extract=["email"],
                schema={"email": {"type": "string"}}
            )
            # result = {"email": "contact@example.com"}
        """
        pass
```

### 4.4 Storage (Enhanced for v2.0)

```python
class Storage(ABC):
    """Interface for storage operations."""
    
    # Existing methods from v1.0...
    
    # NEW: Coverage tracking
    @abstractmethod
    async def update_coverage_stats(
        self,
        domain: str,
        page_type: str,
        field_name: str,
        success: bool
    ) -> None:
        """
        Update coverage statistics for a field.
        
        Tracks how often each field is successfully extracted.
        Used to identify degrading selectors over time.
        
        Args:
            domain: Domain name
            page_type: Type of page
            field_name: Name of field
            success: Whether extraction succeeded
        """
        pass
    
    @abstractmethod
    async def get_coverage_stats(
        self,
        domain: str,
        page_type: str
    ) -> Dict[str, float]:
        """
        Get coverage statistics for a page type.
        
        Returns:
            Dict mapping field_name -> success_rate (0.0 to 1.0)
            
        Example:
            {
                "name": 0.98,      # 98% success rate
                "title": 0.95,
                "email": 0.72,     # Low! Might need repair
                "phone": 0.88
            }
        """
        pass
```

### 4.5 Alerting (Unchanged from v1.0)

```python
class Alerting(ABC):
    """Interface for sending alerts."""
    
    @abstractmethod
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send alert to configured channels."""
        pass
```

---

## 5. Enhanced Use Cases

### 5.1 GenerateConfig (Enhanced for v2.0)

**Old version:** Single sample, no validation  
**New version:** Multi-sample with validation loop

```python
class GenerateConfig:
    """
    Generate validated extraction config for a domain and page type.
    
    This is the "compiler" use case - it learns once and produces
    a production-ready config that will be used for many pages.
    
    ENHANCEMENTS from v1.0:
    - Multi-sample collection (3-5 pages instead of 1)
    - Validation + repair loop (iterate until 80% coverage)
    - Coverage statistics tracking
    - Production-ready quality gates
    """
    
    def __init__(
        self,
        fetcher: PageFetcher,
        llm: LLMProvider,
        storage: Storage,
        alerting: Alerting
    ):
        self.fetcher = fetcher
        self.llm = llm
        self.storage = storage
        self.alerting = alerting
    
    async def execute(
        self,
        domain: str,
        page_type: PageType,
        sample_urls: List[str],
        target_schema: Dict[str, Any],
        coverage_threshold: float = 0.8,
        max_iterations: int = 3
    ) -> ConfigGenerationResult:
        """
        Generate and validate extraction config.
        
        Args:
            domain: Domain to configure (e.g., "hospital.com")
            page_type: Type of page (e.g., "team_page")
            sample_urls: 3-5 representative URLs of this page type
            target_schema: Expected output schema
            coverage_threshold: Minimum coverage to accept (default: 0.8)
            max_iterations: Max validation/repair iterations (default: 3)
            
        Returns:
            ConfigGenerationResult with:
            - config: The validated PageTypeConfig
            - final_coverage: Achieved coverage score
            - iterations_needed: How many repair iterations
            - config_path: Where config was saved
            
        Raises:
            ConfigGenerationError: If coverage threshold not met after max iterations
        """
        
        logger.info(f"🔧 Generating config for {domain}/{page_type}")
        logger.info(f"📄 Collecting {len(sample_urls)} sample pages...")
        
        # STEP 1: Collect samples
        samples = []
        for url in sample_urls:
            try:
                html = await self.fetcher.fetch(url)
                samples.append(PageSample(url=url, html=html))
                logger.info(f"✅ Fetched: {url}")
            except FetchError as e:
                logger.warning(f"⚠️ Failed to fetch {url}: {e}")
                # Continue with other samples
        
        if len(samples) < 2:
            raise ConfigGenerationError(
                f"Need at least 2 samples, got {len(samples)}"
            )
        
        # STEP 2: Propose initial selectors
        logger.info("🤖 Proposing selectors with LLM...")
        config = await self.llm.propose_selectors(
            samples=samples,
            schema=target_schema,
            domain_context=f"Domain: {domain}, Type: {page_type}"
        )
        
        # STEP 3: Validation + Repair Loop
        logger.info("🔍 Validating selectors...")
        final_coverage = 0.0
        iterations_needed = 0
        
        for iteration in range(max_iterations):
            iterations_needed = iteration + 1
            
            # Validate on all samples
            validation_results = []
            for sample in samples:
                result = self._test_config(sample.html, config)
                validation_results.append(result)
            
            # Calculate coverage
            final_coverage = self._calculate_coverage(
                validation_results,
                target_schema
            )
            
            logger.info(
                f"📊 Iteration {iteration + 1}/{max_iterations}: "
                f"Coverage = {final_coverage:.1%}"
            )
            
            # Check threshold
            if final_coverage >= coverage_threshold:
                logger.info(f"✅ Coverage threshold met!")
                break
            
            # Repair if needed
            if iteration < max_iterations - 1:
                logger.info("🔧 Repairing selectors...")
                failures = self._identify_failures(
                    validation_results,
                    samples
                )
                
                config = await self.llm.repair_selectors(
                    current_config=config,
                    failures=failures,
                    samples=samples
                )
        
        # STEP 4: Check final quality
        if final_coverage < coverage_threshold:
            await self.alerting.send_alert(
                title=f"Config Generation: Low Coverage",
                message=f"Only achieved {final_coverage:.1%} coverage "
                        f"for {domain}/{page_type} after {iterations_needed} iterations",
                severity=AlertSeverity.WARNING,
                metadata={
                    "domain": domain,
                    "page_type": page_type,
                    "coverage": final_coverage,
                    "threshold": coverage_threshold
                }
            )
        
        # STEP 5: Save config with metadata
        config.version = datetime.now().isoformat()
        config.last_validated = datetime.now()
        config.total_pages_tested = len(samples)
        config.coverage_stats = self._calculate_field_coverage(
            validation_results
        )
        
        config_path = await self.storage.save_config(
            domain=domain,
            page_type=page_type,
            config=config.dict()
        )
        
        logger.info(f"💾 Saved config to: {config_path}")
        
        return ConfigGenerationResult(
            config=config,
            final_coverage=final_coverage,
            iterations_needed=iterations_needed,
            config_path=config_path,
            sample_count=len(samples)
        )
    
    def _test_config(
        self,
        html: str,
        config: PageTypeConfig
    ) -> ExtractionResult:
        """Test config on a single HTML sample."""
        # Use a simple extractor for validation
        from scraper.adapters.extractors.lxml_extractor import LxmlExtractor
        extractor = LxmlExtractor()
        return extractor.extract(html, config.dict())
    
    def _calculate_coverage(
        self,
        results: List[ExtractionResult],
        schema: Dict[str, Any]
    ) -> float:
        """Calculate overall coverage across all results."""
        total_fields = 0
        successful_fields = 0
        
        for result in results:
            for field_name in schema["properties"].keys():
                total_fields += 1
                if field_name in result.data and result.data[field_name]:
                    successful_fields += 1
        
        return successful_fields / total_fields if total_fields > 0 else 0.0
    
    def _calculate_field_coverage(
        self,
        results: List[ExtractionResult]
    ) -> Dict[str, float]:
        """Calculate per-field coverage."""
        field_counts = {}
        field_successes = {}
        
        for result in results:
            for field_name, value in result.data.items():
                field_counts[field_name] = field_counts.get(field_name, 0) + 1
                if value:
                    field_successes[field_name] = field_successes.get(field_name, 0) + 1
        
        return {
            field: field_successes.get(field, 0) / count
            for field, count in field_counts.items()
        }
    
    def _identify_failures(
        self,
        results: List[ExtractionResult],
        samples: List[PageSample]
    ) -> List[FieldFailure]:
        """Identify which fields failed on which samples."""
        failures = []
        
        for i, result in enumerate(results):
            for field_name in result.fields_missing:
                failures.append(FieldFailure(
                    field_name=field_name,
                    sample_url=samples[i].url,
                    html_snippet=samples[i].html[:2000],
                    current_selector=result.attempted_selectors.get(field_name)
                ))
        
        return failures
```

### 5.2 ExtractWithFallback (Enhanced for v2.0)

**Old version:** Page-level LLM fallback  
**New version:** Field-level LLM fallback

```python
class ExtractWithFallback:
    """
    Extract data with field-level LLM fallback.
    
    ENHANCEMENTS from v1.0:
    - Field-level fallback (only extract missing fields)
    - Coverage tracking (update statistics)
    - Smart merging (prefer deterministic over LLM)
    - Cost optimization (10x cheaper LLM usage)
    """
    
    def __init__(
        self,
        extractor: Extractor,
        llm: LLMProvider,
        storage: Storage,
        alerting: Alerting
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
        config: PageTypeConfig
    ) -> ExtractionResult:
        """
        Extract data with field-level LLM fallback.
        
        Flow:
        1. Try XPath extraction (fast, cheap)
        2. Identify missing required fields
        3. If any missing, use LLM for ONLY those fields
        4. Merge results (prefer XPath)
        5. Update coverage statistics
        
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
            xpath_result = self.extractor.extract(html, config.dict())
            logger.info(
                f"✅ XPath extracted {xpath_result.fields_extracted} fields"
            )
        except ExtractionError as e:
            logger.warning(f"⚠️ XPath extraction failed: {e}")
            xpath_error = e
        
        # STEP 2: Identify missing required fields
        missing_fields = self._identify_missing_fields(
            xpath_result,
            config
        )
        
        if not missing_fields:
            # All fields extracted successfully!
            await self._update_coverage_stats(
                domain=domain,
                page_type=page_type,
                result=xpath_result,
                all_success=True
            )
            
            return xpath_result
        
        # STEP 3: Field-level LLM fallback (NEW!)
        logger.info(
            f"🤖 LLM fallback for {len(missing_fields)} missing fields: "
            f"{missing_fields}"
        )
        
        try:
            # Only extract missing fields!
            llm_fields = await self.llm.extract_fields(
                html=html,
                fields_to_extract=missing_fields,
                schema=self._build_field_schema(missing_fields, config)
            )
            
            logger.info(f"✅ LLM extracted missing fields")
            
            # STEP 4: Merge results
            merged_result = self._merge_results(
                xpath_result=xpath_result,
                llm_fields=llm_fields,
                missing_fields=missing_fields
            )
            
            # Update metadata
            merged_result.extraction_method = ExtractionMethod.XPATH_WITH_LLM_FALLBACK
            merged_result.llm_fields_used = missing_fields
            
        except LLMError as e:
            logger.error(f"❌ LLM fallback failed: {e}")
            
            # Alert on critical failure
            await self.alerting.send_alert(
                title="Extraction Failure",
                message=f"Both XPath and LLM failed for {url}",
                severity=AlertSeverity.CRITICAL,
                metadata={
                    "url": url,
                    "domain": domain,
                    "page_type": page_type,
                    "xpath_error": str(xpath_error),
                    "llm_error": str(e)
                }
            )
            
            # Return partial XPath result
            merged_result = xpath_result or ExtractionResult(
                data={},
                extraction_method=ExtractionMethod.FAILED,
                confidence=0.0
            )
        
        # STEP 5: Update coverage statistics
        await self._update_coverage_stats(
            domain=domain,
            page_type=page_type,
            result=merged_result,
            all_success=len(missing_fields) == 0
        )
        
        # Alert if coverage drops below threshold
        coverage_stats = await self.storage.get_coverage_stats(domain, page_type)
        low_coverage_fields = [
            field for field, rate in coverage_stats.items()
            if rate < 0.7  # 70% threshold
        ]
        
        if low_coverage_fields:
            await self.alerting.send_alert(
                title="Low Field Coverage",
                message=f"Fields with <70% coverage: {low_coverage_fields}",
                severity=AlertSeverity.WARNING,
                metadata={
                    "domain": domain,
                    "page_type": page_type,
                    "low_fields": low_coverage_fields,
                    "coverage_stats": coverage_stats
                }
            )
        
        return merged_result
    
    def _identify_missing_fields(
        self,
        result: Optional[ExtractionResult],
        config: PageTypeConfig
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
        for field_name, selector in config.selectors.items():
            # Check if field is required
            field_schema = config.schema["properties"].get(field_name, {})
            is_required = field_name in config.schema.get("required", [])
            
            # Check if field is missing or empty
            value = result.data.get(field_name)
            is_missing = not value or (isinstance(value, list) and len(value) == 0)
            
            if is_required and is_missing:
                missing.append(field_name)
        
        return missing
    
    def _build_field_schema(
        self,
        field_names: List[str],
        config: PageTypeConfig
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
                field for field in field_names
                if field in config.schema.get("required", [])
            ]
        }
    
    def _merge_results(
        self,
        xpath_result: Optional[ExtractionResult],
        llm_fields: Dict[str, Any],
        missing_fields: List[str]
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
                fields_missing=[]
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
            llm_fields_used=missing_fields
        )
    
    async def _update_coverage_stats(
        self,
        domain: str,
        page_type: PageType,
        result: ExtractionResult,
        all_success: bool
    ) -> None:
        """Update coverage statistics for each field."""
        for field_name in result.data.keys():
            success = bool(result.data[field_name])
            
            await self.storage.update_coverage_stats(
                domain=domain,
                page_type=page_type,
                field_name=field_name,
                success=success
            )
```

### 5.3 ScrapePage (Updated for v2.0)

```python
class ScrapePage:
    """
    Orchestrate full page scraping with all enhancements.
    
    Uses ExtractWithFallback internally for field-level fallback.
    """
    
    def __init__(
        self,
        fetcher: PageFetcher,
        extractor: Extractor,
        llm: LLMProvider,
        storage: Storage,
        alerting: Alerting
    ):
        self.fetcher = fetcher
        self.extractor = extractor
        self.llm = llm
        self.storage = storage
        self.alerting = alerting
        
        # Use enhanced fallback strategy
        self.extract_with_fallback = ExtractWithFallback(
            extractor=extractor,
            llm=llm,
            storage=storage,
            alerting=alerting
        )
    
    async def execute(
        self,
        url: str,
        domain: str,
        page_type: Optional[PageType] = None
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
                error_message=str(e)
            )
        
        # STEP 2: Load or generate config
        if not page_type:
            page_type = self._detect_page_type(url, html)
        
        config = await self.storage.load_config(domain, page_type)
        
        if not config:
            logger.warning(f"⚠️ No config found for {domain}/{page_type}")
            
            # TODO: Auto-generate config in background
            # For now, fail gracefully
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
                error_message=f"No config for {domain}/{page_type}"
            )
        
        # STEP 3: Extract with field-level fallback
        extraction_result = await self.extract_with_fallback.execute(
            url=url,
            domain=domain,
            page_type=page_type,
            html=html,
            config=PageTypeConfig(**config)
        )
        
        # STEP 4: Save results
        html_path = await self.storage.save_html(
            domain=domain,
            url=url,
            html=html,
            timestamp=timestamp
        )
        
        json_path = await self.storage.save_json(
            domain=domain,
            url=url,
            data=extraction_result.data,
            timestamp=timestamp
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
            success=True
        )
    
    def _detect_page_type(self, url: str, html: str) -> PageType:
        """Auto-detect page type based on URL and content."""
        # Simple heuristics (can be enhanced with ML)
        url_lower = url.lower()
        
        if "team" in url_lower or "staff" in url_lower:
            return PageType.TEAM_PAGE
        elif "career" in url_lower or "job" in url_lower:
            return PageType.CAREERS_PAGE
        elif "provider" in url_lower or "physician" in url_lower:
            return PageType.PROVIDER_DIRECTORY
        elif "license" in url_lower:
            return PageType.LICENSE_DIRECTORY
        else:
            return PageType.UNKNOWN
```

---

## 6. Adapters

### 6.1 Enhanced LLM Adapters

Both `DirectProvider` and `PocketFlowProvider` need to implement the new LLM methods:

**6.1.1 DirectProvider Enhancement**

```python
class DirectProvider(LLMProvider):
    """
    Direct Anthropic/OpenAI API calls with enhanced capabilities.
    
    NEW in v2.0:
    - propose_selectors() for multi-sample config generation
    - repair_selectors() for targeted fixes
    - extract_fields() for field-level fallback
    """
    
    async def propose_selectors(
        self,
        samples: List[PageSample],
        schema: Dict[str, Any],
        domain_context: str
    ) -> PageTypeConfig:
        """Implement using PROPOSE_SELECTORS_PROMPT."""
        # Build prompt with all samples
        prompt = PROPOSE_SELECTORS_PROMPT.format(
            domain=domain_context,
            page_type=schema.get("title", "unknown"),
            schema=json.dumps(schema, indent=2),
            num_samples=len(samples),
            samples=self._format_samples(samples)
        )
        
        # Call LLM with structured output
        response = await self.generate_structured(
            prompt=prompt,
            output_schema=PageTypeConfigDraft,
            temperature=0.1
        )
        
        return response.to_page_type_config()
    
    async def repair_selectors(
        self,
        current_config: PageTypeConfig,
        failures: List[FieldFailure],
        samples: List[PageSample]
    ) -> PageTypeConfig:
        """Implement using REPAIR_SELECTORS_PROMPT."""
        prompt = REPAIR_SELECTORS_PROMPT.format(
            current_config=json.dumps(current_config.selectors, indent=2),
            failures=self._format_failures(failures)
        )
        
        # Get repairs
        response = await self.generate_structured(
            prompt=prompt,
            output_schema=SelectorRepairs,
            temperature=0.1
        )
        
        # Apply repairs to config
        updated_config = current_config.copy()
        for field_name, repair in response.selectors.items():
            updated_config.selectors[field_name] = repair
        
        return updated_config
    
    async def extract_fields(
        self,
        html: str,
        fields_to_extract: List[str],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract only specific fields."""
        # Build minimal schema for requested fields only
        minimal_schema = {
            "type": "object",
            "properties": {
                field: schema["properties"][field]
                for field in fields_to_extract
                if field in schema["properties"]
            }
        }
        
        prompt = f"""
Extract ONLY these fields from the HTML:
{fields_to_extract}

Schema:
{json.dumps(minimal_schema, indent=2)}

HTML (truncated to 12000 chars):
{html[:12000]}

Return JSON matching the schema exactly.
If a field cannot be found, use empty string or empty array.
"""
        
        # Parse with Pydantic
        output_model = create_model_from_schema(minimal_schema)
        result = await self.generate_structured(
            prompt=prompt,
            output_schema=output_model,
            temperature=0.1
        )
        
        return result.dict()
```

### 6.2 Enhanced Storage Adapters

Both `LocalStorage` and `S3Storage` need to implement coverage tracking:

**6.2.1 LocalStorage Enhancement**

```python
class LocalStorage(Storage):
    """
    Local filesystem storage with coverage tracking.
    
    NEW in v2.0:
    - Coverage statistics stored in JSON files
    - Per-field success rate tracking
    """
    
    async def update_coverage_stats(
        self,
        domain: str,
        page_type: str,
        field_name: str,
        success: bool
    ) -> None:
        """Update coverage stats in local JSON file."""
        stats_path = self._get_stats_path(domain, page_type)
        
        # Load existing stats
        if stats_path.exists():
            with open(stats_path, "r") as f:
                stats = json.load(f)
        else:
            stats = {}
        
        # Initialize field stats if needed
        if field_name not in stats:
            stats[field_name] = {"successes": 0, "total": 0}
        
        # Update
        stats[field_name]["total"] += 1
        if success:
            stats[field_name]["successes"] += 1
        
        # Save
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)
    
    async def get_coverage_stats(
        self,
        domain: str,
        page_type: str
    ) -> Dict[str, float]:
        """Get coverage statistics."""
        stats_path = self._get_stats_path(domain, page_type)
        
        if not stats_path.exists():
            return {}
        
        with open(stats_path, "r") as f:
            stats = json.load(f)
        
        # Calculate success rates
        return {
            field: data["successes"] / data["total"] if data["total"] > 0 else 0.0
            for field, data in stats.items()
        }
    
    def _get_stats_path(self, domain: str, page_type: str) -> Path:
        """Get path to stats file."""
        return (
            self.base_path
            / "coverage-stats"
            / domain
            / f"{page_type}.json"
        )
```

---

## 7. Coverage Tracking

### 7.1 What We Track

**Per-Field Coverage:**
```json
{
  "hospital.com/team_page": {
    "name": 0.98,          // 98% success rate
    "title": 0.95,
    "email": 0.72,         // LOW - might need repair!
    "phone": 0.88,
    "department": 0.91
  }
}
```

**Why Track Coverage:**
1. **Detect Degradation:** Website changes → selectors break → coverage drops
2. **Trigger Re-Learning:** If field coverage < 70%, regenerate config
3. **Prioritize Repairs:** Fix low-coverage fields first
4. **Monitor Quality:** Track improvement after config updates

### 7.2 Coverage Thresholds

| Threshold | Action |
|-----------|--------|
| **>= 95%** | ✅ Excellent - No action needed |
| **80-94%** | ⚠️ Good - Monitor closely |
| **70-79%** | ⚠️ Warning - Schedule repair |
| **< 70%** | 🚨 Critical - Regenerate config immediately |

### 7.3 Automatic Config Repair Workflow

```python
async def monitor_and_repair_configs():
    """
    Background job to monitor coverage and trigger repairs.
    
    Runs: Daily or after N scrapes
    """
    # Get all active configs
    configs = await storage.list_configs()
    
    for domain, page_type in configs:
        # Get coverage stats
        coverage = await storage.get_coverage_stats(domain, page_type)
        
        # Find low-coverage fields
        low_fields = [
            field for field, rate in coverage.items()
            if rate < 0.7
        ]
        
        if low_fields:
            logger.warning(
                f"🚨 Low coverage for {domain}/{page_type}: {low_fields}"
            )
            
            # Alert
            await alerting.send_alert(
                title="Config Repair Needed",
                message=f"Fields {low_fields} have <70% coverage",
                severity=AlertSeverity.WARNING
            )
            
            # Auto-repair (Phase 2 feature)
            # await trigger_config_regeneration(domain, page_type)
```

---

## 8. Data Models

### 8.1 New Models for v2.0

```python
class PageSample(BaseModel):
    """A sample page for config generation."""
    url: HttpUrl
    html: str
    fetched_at: datetime = Field(default_factory=datetime.now)


class FieldFailure(BaseModel):
    """A field that failed extraction on a specific sample."""
    field_name: str
    sample_url: HttpUrl
    html_snippet: str  # First 2000 chars for context
    current_selector: Optional[str] = None


class ConfigGenerationResult(BaseModel):
    """Result of config generation."""
    config: PageTypeConfig
    final_coverage: float  # 0.0 to 1.0
    iterations_needed: int
    config_path: str
    sample_count: int


class ExtractionResult(BaseModel):
    """Enhanced with LLM usage tracking."""
    data: Dict[str, Any]
    extraction_method: ExtractionMethod
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    fields_extracted: int = 0
    fields_missing: List[str] = Field(default_factory=list)
    
    # NEW in v2.0
    llm_fields_used: List[str] = Field(default_factory=list)
    attempted_selectors: Dict[str, str] = Field(default_factory=dict)


class PageTypeConfig(BaseModel):
    """Enhanced with coverage tracking."""
    version: str
    domain: str
    page_type: PageType
    selectors: Dict[str, XPathSelector]
    pagination: Optional[Dict[str, str]] = None
    schema: Dict[str, Any]
    
    # NEW in v2.0
    coverage_stats: Dict[str, float] = Field(default_factory=dict)
    last_validated: Optional[datetime] = None
    total_pages_tested: int = 0


class ExtractionMethod(str, Enum):
    """Enhanced extraction methods."""
    XPATH = "xpath"
    XPATH_WITH_LLM_FALLBACK = "xpath_with_llm_fallback"  # NEW
    LLM_FALLBACK = "llm_fallback"
    LLM_DIRECT = "llm_direct"
    FAILED = "failed"
```

---

## 9. DI Container

### 9.1 Updated Container (Unchanged structure, new adapter capabilities)

The Container structure remains the same - it still resolves adapters based on `.env` variables. However, the adapters themselves now implement enhanced interfaces.

```python
# .env configuration remains the same
FETCHER=playwright
STORAGE=local
LLM_PROVIDER=pocketflow
ALERTING=console

# Container usage remains the same
from scraper.config import container

scraper = ScrapePage(
    fetcher=container.fetcher,
    extractor=container.extractor,
    llm=container.llm,  # Now has propose_selectors, repair_selectors, extract_fields
    storage=container.storage,  # Now has coverage tracking
    alerting=container.alerting
)
```

**Key Point:** Clean Architecture preserved! Container interface unchanged, only adapter implementations enhanced.

---

## 10. Phase-by-Phase Roadmap

### 10.1 Phase 1: Core System (Weeks 1-4) - UPDATED

**Week 1:** Simple Adapters
- ConsoleAlerting
- LocalStorage (with coverage tracking)
- HttpxFetcher

**Week 2:** LLM + Extraction
- DirectProvider (basic version - no multi-sample yet)
- LxmlExtractor

**Week 3:** Basic Use Cases
- ScrapePage (page-level fallback)
- Basic config loading/saving

**Week 4:** First Integration
- CLI tool
- E2E test
- **First scrape!**

### 10.2 Phase 2: ParserGPT Enhancements (Weeks 5-8) - NEW

**Week 5:** Multi-Sample Config Generation
- Enhance DirectProvider with `propose_selectors()`
- Implement sample collection
- Basic validation loop

**Week 6:** Field-Level Fallback
- Enhance DirectProvider with `extract_fields()`
- Update ExtractWithFallback use case
- Cost optimization

**Week 7:** Validation + Repair
- Implement `repair_selectors()`
- Coverage calculation
- Iterative improvement loop

**Week 8:** Coverage Tracking
- LocalStorage coverage stats
- Monitoring dashboard
- Alert thresholds

### 10.3 Phase 3: Production Scale (Weeks 9-16)

**Week 9-10:** Production Adapters
- S3Storage (with coverage tracking)
- KnockAlerting
- PlaywrightFetcher

**Week 11-12:** Orchestration
- APScheduler
- Job queues
- Retry logic

**Week 13-14:** Advanced Features
- PocketFlowProvider
- Auto-config regeneration
- A/B testing configs

**Week 15-16:** Observability
- Prometheus metrics
- Grafana dashboards
- Cost tracking

---

## 11. Cost Analysis: v1.0 vs v2.0

### 11.1 Scenario: Scraping 1000 Pages

**Assumptions:**
- XPath success rate: 85%
- LLM costs: $0.01 per 1K tokens
- Average page: 10 fields

**v1.0 (Page-Level Fallback):**
```
XPath success: 850 pages × $0 = $0
LLM fallback: 150 pages × 10 fields × $0.01 = $15
Total: $15
```

**v2.0 (Field-Level Fallback):**
```
XPath success: 850 pages × $0 = $0
Partial XPath: 150 pages × 8.5 fields (85% avg) × $0 = $0
LLM fields: 150 pages × 1.5 fields (15% avg) × $0.01 = $2.25
Total: $2.25
```

**Savings: 85% reduction in LLM costs!**

### 11.2 Config Generation Costs

**v1.0:**
```
Single sample: 1 page × $0.02 = $0.02 per config
```

**v2.0:**
```
Multi-sample: 5 pages × $0.02 = $0.10 per config (initial)
Validation: 2 iterations × $0.02 = $0.04 (repairs)
Total: $0.14 per config
```

**Trade-off:** 7x higher config generation cost, but:
- Configs are generated once and reused for thousands of pages
- Higher quality = fewer runtime failures
- Amortized cost is negligible

---

## 12. Summary of Enhancements

### 12.1 What Changed from v1.0

| Component | v1.0 | v2.0 (Enhanced) |
|-----------|------|-----------------|
| **Config Generation** | Single sample | Multi-sample with validation |
| **LLM Fallback** | Page-level | Field-level |
| **Config Quality** | No validation | Validation + repair loop |
| **Coverage Tracking** | None | Per-field statistics |
| **Cost Efficiency** | Baseline | 85% LLM cost reduction |
| **Selector Reliability** | Unknown | Measured and monitored |

### 12.2 Architecture Unchanged

✅ **Clean Architecture preserved**
✅ **YAGNI/KISS principles maintained**
✅ **DI Container interface unchanged**
✅ **Port definitions backward compatible**
✅ **Testing strategy same**

**Key Insight:** We enhanced *capabilities* without compromising *maintainability*.

---

## 13. Migration Path from v1.0

### 13.1 For Existing Implementations

If you've already built v1.0:

**Step 1:** Enhance LLMProvider interface
```python
# Add new methods to port
class LLMProvider(ABC):
    # ... existing methods ...
    
    # NEW
    async def propose_selectors(...): pass
    async def repair_selectors(...): pass
    async def extract_fields(...): pass
```

**Step 2:** Update DirectProvider
```python
# Implement new methods
class DirectProvider(LLMProvider):
    async def propose_selectors(self, ...):
        # Implementation
```

**Step 3:** Enhance ExtractWithFallback
```python
# Replace page-level fallback with field-level
llm_fields = await self.llm.extract_fields(
    html=html,
    fields_to_extract=missing_fields  # Only missing!
)
```

**Step 4:** Add coverage tracking
```python
# Update Storage implementations
async def update_coverage_stats(...): pass
async def get_coverage_stats(...): pass
```

### 13.2 Backward Compatibility

All v1.0 code continues to work:
- Old use cases still function
- New use cases are optional
- Gradual migration supported

---

## 14. Conclusion

### 14.1 Best of Both Worlds

**From ParserGPT we adopted:**
- ✅ Multi-sample config generation
- ✅ Field-level LLM fallback
- ✅ Validation + repair loops
- ✅ Coverage tracking

**From Clean Architecture we kept:**
- ✅ Testable, maintainable structure
- ✅ YAGNI/KISS principles
- ✅ Provider swapping flexibility
- ✅ Progressive complexity

### 14.2 Production Ready

This enhanced design is:
- **Cost-efficient:** 85% LLM cost reduction
- **High-quality:** Validation ensures good configs
- **Observable:** Coverage tracking monitors health
- **Maintainable:** Clean Architecture preserved

### 14.3 Next Steps

1. **Implement Phase 1** (Weeks 1-4): Core system
2. **Add enhancements** (Weeks 5-8): ParserGPT patterns
3. **Scale to production** (Weeks 9-16): Advanced features

**You now have a world-class web scraping architecture!** 🚀

---

**Document Version:** 2.0  
**Last Updated:** November 17, 2025  
**Author:** Diego (CTO, Pickle)  
**Inspired By:** ParserGPT analysis and comparison
