# LLM Web Scraper v2.0

Intelligent web scraping system that combines deterministic XPath extraction with LLM-powered field-level fallback. The LLM acts as a "compiler" that generates extraction rules, not as a runtime extractor -- dramatically reducing cost while maintaining high accuracy.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the demo (no API key needed)
make demo
```

The demo runs three scenarios against bundled HTML fixtures:

1. **Quotes page** -- multi-item XPath extraction (quotes, authors, tags)
2. **Book detail** -- single-item extraction (title, price, UPC, description)
3. **Broken selector** -- shows field-level LLM fallback when one XPath breaks

To run against live websites instead of fixtures:

```bash
make demo-live
```

## How It Works

```
XPath extraction (fast, free)
        |
        v
  All fields OK? ──yes──> Done
        |
       no
        v
Send ONLY missing fields to LLM (cheap)
        |
        v
  Merge results, update coverage stats
```

The key insight: when a selector breaks, only **that field** goes to the LLM, not the entire page. At scale this saves ~85% vs page-level LLM extraction.

## Project Status

### Phase 1: Core System -- Complete

| Component | Status | Details |
|-----------|--------|---------|
| Domain models | Done | Pydantic models, custom exceptions |
| Ports (interfaces) | Done | 5 ABCs: Fetcher, Extractor, LLM, Storage, Alerting |
| httpx fetcher | Done | Async HTTP GET |
| lxml extractor | Done | XPath + CSS selector extraction |
| Direct LLM provider | Done | Anthropic API (`extract_fields` only) |
| Local storage | Done | Filesystem with coverage tracking |
| Console alerting | Done | Stdout alerts |
| ExtractWithFallback | Done | Field-level LLM fallback use case |
| ScrapePage | Done | End-to-end orchestration |
| CLI | Done | `scraper scrape URL`, `scraper info` |
| Tests | Done | 42 tests passing (33 unit + 9 integration) |

### Phase 2: ParserGPT Enhancements -- Not Started

- Multi-sample config generation (3-5 pages for robust selectors)
- `propose_selectors()` / `repair_selectors()` in LLM provider
- Validation + repair loops
- GenerateConfig use case

### Phase 3: Scale -- Not Started

- Playwright fetcher (JavaScript-heavy sites)
- S3 storage, Knock alerting
- PocketFlow LLM orchestration

## Architecture

Clean Architecture with dependency injection. Swap any provider via `.env` with zero code changes.

```
scraper/
├── domain/             # Models, exceptions (no external deps)
├── ports/              # Abstract interfaces (5 ABCs)
├── adapters/           # Concrete implementations
│   ├── fetchers/       #   httpx (done), playwright (Phase 3)
│   ├── extractors/     #   lxml (done)
│   ├── llm/            #   direct Anthropic/OpenAI (done)
│   ├── storage/        #   local filesystem (done), S3 (Phase 3)
│   └── alerting/       #   console (done), Knock (Phase 3)
├── use_cases/          # Business workflows
│   ├── scrape_page.py          # End-to-end orchestration
│   └── extract_with_fallback.py # Field-level LLM fallback
├── config.py           # DI container
└── cli.py              # Click CLI

demo/                   # Demo fixtures and script
tests/
├── unit/               # 33 tests, mocked deps
└── integration/        # 9 tests, real adapters
```

## Development

```bash
make test               # Unit tests
make test-integration   # Integration tests
make test-all           # Everything
make lint               # Ruff + mypy
make format             # Black
make demo               # Run demo offline
```

## Configuration

```bash
cp .env.example .env
```

| Variable | Default | Options |
|----------|---------|---------|
| `FETCHER` | `httpx` | `httpx`, `playwright` |
| `STORAGE` | `local` | `local`, `s3` |
| `LLM_PROVIDER` | `direct` | `direct`, `pocketflow` |
| `ALERTING` | `console` | `console`, `knock` |
| `ANTHROPIC_API_KEY` | -- | Required for LLM fallback |

## Cost at Scale

At 100 domains, 10k pages/month each:

| Approach | Annual Cost |
|----------|------------|
| Page-level LLM (v1.0) | $18,000 |
| Field-level fallback (v2.0) | $2,820 |
| **Savings** | **$15,180/yr** |

## Documentation

- [System Design v2.0](docs/SYSTEM_DESIGN_LLM_Web_Scraper_v2.0.md) -- Complete technical spec
- [ParserGPT Comparison](docs/ParserGPT_Comparison.md) -- Design rationale
- [Update Summary](docs/UPDATE_SUMMARY.md) -- What changed from v1.0
- [ADR-006: ParserGPT Enhancements](docs/adr/ADR-006-ParserGPT-Enhancements.md)

---

**Version:** 2.0 | **Author:** Diego | **License:** Apache 2.0
