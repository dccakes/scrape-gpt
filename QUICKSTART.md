# Quick Start Guide

Get up and running in under 5 minutes.

## 1. Install

```bash
pip install -e ".[dev]"
```

Or with uv:

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## 2. Run the Demo

```bash
make demo
```

No API key needed. This runs three extraction scenarios against bundled HTML fixtures from quotes.toscrape.com and books.toscrape.com:

1. Multi-item XPath extraction (quotes, authors, tags)
2. Single-item detail page extraction (title, price, UPC, etc.)
3. Broken selector triggering field-level LLM fallback

## 3. Run the Tests

```bash
make test           # 33 unit tests
make test-all       # 42 total (unit + integration)
```

## 4. Scrape a Real Page

To scrape a page you need:
- A config file with XPath selectors (in `data/configs/<domain>/<page_type>.json`)
- An `ANTHROPIC_API_KEY` in `.env` (only if LLM fallback is needed)

```bash
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY

scraper scrape https://quotes.toscrape.com/ -t quotes_page
```

See `data/configs/` for example config files.

## 5. Create a Config for a New Site

Configs are JSON files that tell the extractor which XPath/CSS selectors to use:

```json
{
  "version": "2.0",
  "domain": "example.com",
  "page_type": "team_page",
  "selectors": {
    "name":  { "xpath": "//h1[@class='name']/text()" },
    "title": { "xpath": "//div[@class='title']/text()" },
    "email": { "xpath": "//a[contains(@href, 'mailto:')]/text()" }
  },
  "schema": {
    "type": "object",
    "properties": {
      "name":  { "type": "string" },
      "title": { "type": "string" },
      "email": { "type": "string" }
    },
    "required": ["name", "email"]
  },
  "coverage_stats": {},
  "total_pages_tested": 0
}
```

Save it to `data/configs/example.com/team_page.json` and you're ready to scrape.

Tip: use your browser's DevTools (Inspect Element > Copy XPath) to find selectors.

## 6. Project Layout

```
scraper/
├── domain/          # Models and exceptions
├── ports/           # Abstract interfaces
├── adapters/        # Implementations (httpx, lxml, Anthropic, etc.)
├── use_cases/       # Business logic (ScrapePage, ExtractWithFallback)
├── config.py        # DI container -- swap providers via .env
└── cli.py           # CLI entry point

demo/                # Demo script and HTML fixtures
data/configs/        # XPath configs per domain/page_type
tests/               # 42 tests (unit + integration)
```

## 7. Key Make Targets

```bash
make demo               # Run demo (offline)
make demo-live          # Run demo against live sites
make test               # Unit tests
make test-all           # All tests
make lint               # Ruff + mypy
make format             # Black formatting
```

## Next Steps

- Read the [System Design](docs/SYSTEM_DESIGN_LLM_Web_Scraper_v2.0.md) for the full technical spec
- Look at `demo/run_demo.py` to understand the extraction pipeline
- Create configs for your target sites and start scraping
