# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a graph-native entity resolution system for healthcare professional data that processes 500K+ records in under 30 minutes. The system uses PostgreSQL for storage, DuckDB for high-performance analytics, Parquet for intermediate data, and NetworkX for clustering.

**Key Performance Targets:**
- Full resolution (500K entities): <30 minutes (16x faster than legacy)
- Incremental updates (5K entities): <5 minutes (12x faster than legacy)
- Precision: >95%, Recall: >90%

## Essential Development Commands

### Environment Setup
- `make setup` - Install dependencies with uv and configure pre-commit hooks
- `make dev` - Start development environment
- `make down` - Stop all services
- `make clean` - Clean up environment including volumes
- `make rebuild` - Complete rebuild of development environment

### Database Operations
- `make migrate` - Apply all pending Alembic migrations
- `make db-reset` - Reset database and reapply migrations
- `make migrate-create message="description"` - Create new migration file

### Data Pipeline Operations
- `make ingest source=colorado_pt file=data.csv` - Run ingestion for a source
- `make export type=full` - Export entities to Parquet (full or incremental)
- `make resolve entity_type=person` - Run entity resolution
- `make import run_id=<id>` - Import resolved clusters

### Testing & Code Quality
- `make test` - Run unit tests with pytest (excludes integration tests)
- `make test-integration` - Run integration tests
- `make test-all` - Run all tests
- `make test-performance` - Run performance benchmarks
- `make lint` - Run ruff and mypy checks
- `make lint-fix` - Auto-fix linting issues with ruff

### Monitoring
- `make metrics` - View OpenTelemetry metrics
- `make logs component=resolution` - View logs for specific component

## Architecture Overview

### Core Architectural Principles

**Clean Architecture:** Domain-driven design with clear separation of concerns
- Domain layer (business logic) is independent of infrastructure
- Dependencies point inward: API → Services → Domain
- Use cases orchestrate business workflows

**YAGNI (You Aren't Gonna Need It):** Build only what's specified
- No speculative features
- No premature optimization
- Stick to the specifications (see `/docs/specifications/`)

**Test-Driven Development:** All code written via Red-Green-Refactor
- Write failing test first (RED)
- Write minimal code to pass (GREEN)
- Refactor if valuable (REFACTOR)

### System Architecture

The system follows a **four-phase pipeline**:

```
Phase 1: INGESTION        Phase 2: EXPORT           Phase 3: RESOLUTION       Phase 4: IMPORT
CSV → PostgreSQL    →    PostgreSQL → Parquet  →    DuckDB Processing    →    PostgreSQL Profiles
(Quality + Lineage)      (Graph Format)            (Matching + Clustering)   (Serving Layer)
```

### Directory Structure

```
pickle-entity-resolution/
├── src/
│   ├── ingestion/          # Phase 1: CSV → PostgreSQL
│   │   ├── ingestion_service.py
│   │   ├── quality_validator.py
│   │   └── hash_computer.py
│   ├── export/             # Phase 2: PostgreSQL → Parquet
│   │   ├── export_service.py
│   │   ├── query_builder.py
│   │   ├── schema_converter.py
│   │   └── parquet_writer.py
│   ├── resolution/         # Phase 3: DuckDB entity resolution
│   │   ├── resolution_engine.py
│   │   ├── blocking_service.py
│   │   ├── candidate_generator.py
│   │   ├── graph_context_service.py
│   │   ├── matching_service.py
│   │   └── clustering_service.py
│   ├── import/             # Phase 4: Clusters → PostgreSQL
│   │   ├── import_service.py
│   │   ├── cluster_differ.py
│   │   └── database_updater.py
│   ├── db/
│   │   └── models/         # SQLAlchemy models
│   │       ├── person.py
│   │       ├── medical_license.py
│   │       ├── data_pull.py
│   │       ├── entity_cluster.py
│   │       └── cluster_membership.py
│   ├── domain/             # Domain models and interfaces
│   │   └── enums/
│   ├── config/             # Configuration loaders
│   └── observability/      # OpenTelemetry setup
├── config/
│   ├── sources/            # YAML source configurations
│   ├── entities/           # YAML entity configurations
│   └── quality_rules/      # YAML quality validation rules
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── synthetic_data.py
├── docs/
│   └── specifications/     # Complete specification suite
│       ├── 00-SYSTEM-OVERVIEW.md
│       ├── 01-INGESTION-SPECS.md
│       ├── 02-EXPORT-SPECS.md
│       ├── 03-RESOLUTION-SPECS.md
│       ├── 04-IMPORT-SPECS.md
│       └── 05-MIGRATION-SPECS.md
└── alembic/                # Database migrations
```

### Key Architectural Patterns

#### Service Layer
Each pipeline phase has a primary service class that orchestrates the workflow:
- `IngestionService`: CSV parsing → validation → PostgreSQL
- `ExportService`: PostgreSQL → Parquet export
- `ResolutionEngine`: DuckDB-based entity resolution
- `ImportService`: Resolved clusters → PostgreSQL

Services are stateless and dependency-injected. They coordinate between repositories, domain logic, and external systems.

#### Repository Pattern
Repositories handle database access (PostgreSQL only):
- `DataPullRepository`
- `EntityRepository` (base class)
- `PersonRepository`
- `MedicalLicenseRepository`
- `EntityClusterRepository`
- `ClusterMembershipRepository`

**Guidelines:**
- Always use `session.flush()` after write operations
- Keep business logic in use cases/services, not repositories
- Repositories can reference other repositories
- Use async/await for all database operations

#### Domain Models
Domain models represent business concepts and rules:
- Dataclasses for requests/results (e.g., `IngestionRequest`, `ResolutionResult`)
- Stats objects (e.g., `BlockingStats`, `MatchingStats`)
- Enums for controlled vocabularies

**Guidelines:**
- Keep domain logic independent of infrastructure
- No database dependencies in domain layer
- Domain models validate their own invariants

#### Configuration Management
Three types of configuration:
1. **Source configs** (`config/sources/*.yaml`): Define CSV parsing and field mappings
2. **Entity configs** (`config/entities/*.yaml`): Define blocking rules, comparison pipelines
3. **Quality rules** (`config/quality_rules/*.yaml`): Define validation rules

All configs are YAML-based and loaded at runtime. Changes require service restart.

### Data Flow & Schemas

#### PostgreSQL Schema (Storage Layer)

**pickle_data schema:**
- `data_sources`: Source metadata
- `data_pulls`: Ingestion run tracking
- `data_records`: Raw records
- `people`, `medical_licenses`, `external_organizations`, `places`, `contact_information`: Entity tables (with lineage fields)
- `record_entities`: Many-to-many relationship table
- `entity_clusters`: Resolved clusters
- `cluster_membership`: Entity-to-cluster assignments
- `resolution_runs`: Resolution run metadata

**Key Fields Added to All Entity Tables:**
- `pull_id` (UUID): Links to data_pulls
- `source_record_hash` (String): SHA-256 for deduplication
- `quality_flags` (JSONB): Quality validation results
- `used_in_matching` (Boolean): Include in resolution

#### Parquet Schema (Compute Layer)

**nodes.parquet:**
- Common fields: id, type, pull_id, source_id, quality_flags, used_in_matching
- Type-specific fields: given_name, family_name (person), license_number (license), etc.

**edges.parquet:**
- from_id, to_id, edge_type (issued_to, employed_by, located_at, same_as)
- Temporal: valid_from, valid_to
- Properties: confidence, metadata (JSONB)

#### DuckDB Processing
DuckDB loads Parquet files for in-memory analytics:
- Blocking key generation (SQL + UDFs)
- Candidate pair generation (self-join)
- Graph context enrichment (lateral joins)
- Match scoring (comparison pipelines)
- Results exported back to Parquet

## Testing Strategy

### Test-Driven Development (MANDATORY)

**Every feature MUST follow Red-Green-Refactor:**

1. **RED:** Write a failing test based on specification (SPEC-XXX)
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

Tests map to specifications in `/docs/specifications/`:

```
Specification: SPEC-T1-030
Test: TDD-T1-030 in tests/unit/test_ingestion/test_entity_models.py
```

**Test Categories:**
- `unit`: Fast, isolated tests (services, domain logic, repositories)
- `integration`: End-to-end tests (full pipeline, database, S3)
- `performance`: Benchmarks (must meet spec targets)

**Example Test Structure:**
```python
# tests/unit/test_ingestion/test_quality_validator.py

def test_validator_detects_missing_required_fields():
    """TDD-T1-053: GIVEN person missing family_name, WHEN validated, 
    THEN validation fails with missing_required_fields error."""
    # Arrange
    validator = QualityValidator(config_dir="config/quality_rules")
    person_data = {"given_name": "John"}  # Missing family_name
    
    # Act
    result = validator.validate("person", person_data)
    
    # Assert
    assert result.is_valid == False
    assert "family_name" in result.missing_required_fields
```

### Test Environment
- Temporary PostgreSQL database per test session
- Alembic migrations applied automatically
- Factory pattern for test data (`tests/fixtures/synthetic_data.py`)
- Mock S3 using moto or local filesystem

### Running Tests
```bash
# Run all unit tests
make test

# Run specific test file
uv run pytest tests/unit/test_ingestion/test_quality_validator.py

# Run tests matching a pattern
uv run pytest -k "validator"

# Run with coverage
uv run pytest --cov=src tests/

# Run integration tests (slower)
make test-integration
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

- Functions: `snake_case`, verb-based (`calculate_match_score`, `validate_entity`)
- Classes: `PascalCase` (`QualityValidator`, `IngestionService`)
- Constants: `UPPER_SNAKE_CASE` for true constants
- Files: `snake_case.py`
- Test files: `test_*.py`

### Type Hints

**Required for all function signatures:**
```python
def compute_hash(record: dict[str, Any]) -> str:
    """Compute SHA-256 hash of record."""
    ...

async def ingest_source(
    self,
    source_slug: str,
    file_path: str,
    batch_size: int = 1000
) -> IngestionResult:
    """Run ingestion pipeline."""
    ...
```

### Comments & Documentation

**Code should be self-documenting.** Comments indicate unclear code.

**Docstrings:** Use for public APIs and complex algorithms
```python
def generate_blocking_keys(self, entity_type: str) -> BlockingStats:
    """Generate blocking keys for entity type using YAML-configured rules.
    
    Applies each blocking rule in priority order, generates keys via SQL,
    filters oversized blocks, and stores in blocking_keys table.
    
    Args:
        entity_type: Type of entity (person, license, organization)
    
    Returns:
        BlockingStats with block counts and size distribution
    """
```

**Inline comments:** Only when absolutely necessary to explain "why", never "what"

### Error Handling

**Use custom domain exceptions:**
```python
# src/domain/errors.py
class IngestionError(Exception):
    """Raised when ingestion pipeline fails."""
    
class QualityValidationError(Exception):
    """Raised when validation rules violated."""
```

**Log errors with context:**
```python
try:
    result = await service.ingest(request)
except IngestionError as e:
    logger.error(f"Ingestion failed for {request.source_slug}: {e}")
    raise
```

## Working with Specifications

### Specification Structure

All system behavior is defined in `/docs/specifications/`:
- **SPEC-XXX:** Defines what the system should do
- **TDD-XXX:** Defines what tests should verify

**Example:**
```
SPEC-T1-053: The QualityValidator SHALL detect missing required fields.

TDD-T1-053: Tests SHALL verify that when an entity is missing a required 
field, validation fails with the field listed in missing_required_fields.
```

### Implementation Process

1. **Read specification document** for the component you're building
2. **Identify the task** (e.g., T1-12: Implement Quality Validator)
3. **Review all SPEC-XXX for that task** to understand requirements
4. **Review all TDD-XXX for that task** to understand test requirements
5. **Write tests first** (RED) based on TDD-XXX specs
6. **Implement feature** (GREEN) to satisfy SPEC-XXX specs
7. **Refactor** if valuable
8. **Update docs** if you've made meaningful changes

### When Specifications Are Unclear

**Don't guess. Ask.**

If a specification is ambiguous or conflicting:
1. Stop and ask for clarification
2. Document the ambiguity
3. Propose 2-3 specific options
4. Wait for decision before implementing

## Key Development Workflows

### Adding a New Data Source

1. Create source config YAML in `config/sources/`
2. Add entry to `config/config_registry.json`
3. Write tests for transformation
4. Run ingestion: `make ingest source=new_source file=data.csv`
5. Validate data quality metrics

### Adding a New Entity Type

1. Create SQLAlchemy model in `src/db/models/`
2. Create entity config YAML in `config/entities/`
3. Create quality rules YAML in `config/quality_rules/`
4. Create migration: `make migrate-create message="add new entity type"`
5. Update export/resolution services
6. Write tests for full pipeline

### Adding a New Comparison Rule

1. Update entity config YAML (`config/entities/*.yaml`)
2. Add field comparator definition
3. If custom logic needed, add comparator to `ComparatorRegistry`
4. Write tests for comparison behavior
5. Validate against sample data

### Debugging Resolution Issues

1. Check blocking: Are candidate pairs being generated?
   - Query: `SELECT * FROM blocking_keys WHERE entity_id = ?`
2. Check matching: Are pairs being scored correctly?
   - Enable debug logging in `MatchingService`
3. Check clustering: Are clusters formed correctly?
   - Export cluster graph, visualize with NetworkX
4. Check metrics: Review `resolution_runs` table

### Performance Optimization

**Only optimize if measurements show a problem.**

1. Measure baseline performance
2. Identify bottleneck (profiling, metrics)
3. Implement optimization
4. Measure improvement
5. Document in code why optimization was needed

**Common optimizations:**
- Batch size tuning (default 1000)
- DuckDB row group size (default 100,000)
- Blocking rule tuning (max_block_size)
- Parallel processing (careful with I/O)

## Database Migrations

### Creating Migrations

```bash
# Create new migration
make migrate-create message="add lineage fields to entities"

# Review generated migration in alembic/versions/
# Edit upgrade() and downgrade() functions

# Apply migration
make migrate

# Test rollback
alembic downgrade -1
```

### Migration Guidelines

- **Descriptive messages:** Explain what and why
- **Test both directions:** Apply (upgrade) and rollback (downgrade)
- **Idempotent:** Safe to run multiple times
- **Small changes:** One logical change per migration
- **Data migrations:** Separate schema from data changes

## Observability

### OpenTelemetry Integration

All components emit structured events:
```python
from src.observability import tracer

with tracer.start_as_current_span("ingestion.batch_processed") as span:
    span.set_attribute("batch_number", batch_num)
    span.set_attribute("records_processed", len(batch))
```

### Metrics to Monitor

**Ingestion:**
- `ingestion.records_processed` (counter)
- `ingestion.records_quarantined` (counter)
- `ingestion.duration_seconds` (histogram)

**Resolution:**
- `resolution.candidate_pairs` (gauge)
- `resolution.matches_found` (counter)
- `resolution.duration_seconds` (histogram)

**Data Quality:**
- `quality.completeness_score` (histogram)
- `quality.quarantine_rate` (gauge)

### Logging Best Practices

```python
import structlog
logger = structlog.get_logger()

# Structured logging
logger.info(
    "ingestion_completed",
    source_slug=request.source_slug,
    records_processed=result.records_processed,
    duration_seconds=duration
)

# Error logging with context
logger.error(
    "resolution_failed",
    entity_type=entity_type,
    error=str(e),
    stack_trace=traceback.format_exc()
)
```

## Working with Claude Code

### Expectations

When working on this codebase:

1. **ALWAYS FOLLOW TDD** - No production code without a failing test first
2. **Read specifications first** - Understand requirements before coding
3. **Ask clarifying questions** - Don't assume or guess
4. **Think from first principles** - Understand the "why" behind requirements
5. **Keep it simple** - YAGNI applies to everything
6. **Update docs** - Keep project documentation current

### Before Making Changes

1. Read relevant specification document
2. Understand the full context
3. Review existing tests
4. Identify what tests need to be written
5. Write tests (RED)
6. Implement (GREEN)
7. Refactor if valuable
8. Update docs if needed

### When Stuck

1. Review specifications for clarity
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

### Machine Learning Placeholder

Specifications include ML interfaces but MVP uses deterministic rules. Do not implement ML features unless explicitly specified.

### Graph Context ("Smoking Guns")

This is a key differentiator. Cross-entity evidence (e.g., same license) is MORE important than direct attribute comparison. Always consider graph context in matching logic.

### Performance Targets Are Hard Requirements

- Full resolution: <30 minutes for 500K entities
- Incremental: <5 minutes for 5K entities
- If targets aren't met, optimization is REQUIRED

### Data Quality Is Critical

- Quarantine rate should be <5%
- Precision >95%, Recall >90%
- If quality degrades, stop and investigate

## Quick Reference

### Common Tasks

```bash
# Start fresh
make clean && make rebuild && make migrate

# Run full pipeline
make ingest source=colorado_pt file=data.csv
make export type=full
make resolve entity_type=person
make import run_id=<id>

# Run tests for component
uv run pytest tests/unit/test_ingestion/
uv run pytest tests/unit/test_resolution/

# Check code quality
make lint
make lint-fix

# View logs
make logs component=ingestion
make logs component=resolution
```

### Key Files

- `/docs/specifications/README.md` - Specification index
- `config/config_registry.json` - Config file registry
- `src/db/models/` - Database models
- `tests/fixtures/synthetic_data.py` - Test data generation

---

**Remember: Specifications define behavior. Tests verify behavior. Code implements behavior. In that order.**
