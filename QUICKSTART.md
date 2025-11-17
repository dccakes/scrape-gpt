# Quick Start Guide - v2.0

Get up and running with the enhanced LLM Web Scraper in 5 minutes.

## What's New in v2.0?

- ✅ **Multi-sample config generation** (3-5 pages for robust selectors)
- ✅ **Field-level LLM fallback** (85% cost reduction!)
- ✅ **Validation + repair loops** (quality gates)
- ✅ **Coverage tracking** (health monitoring)

**Read full details:** [UPDATE_SUMMARY.md](docs/UPDATE_SUMMARY.md)

## 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 2. Setup Project

```bash
# Navigate to project
cd llm-scraper-starter-v2

# Create virtual environment
uv venv

# Activate
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
uv pip install -e ".[dev]"

# Install Playwright (if using browser)
playwright install chromium
```

## 3. Configure

```bash
# Copy example
cp .env.example .env

# Edit with your API keys
# Minimum required: ANTHROPIC_API_KEY or OPENAI_API_KEY
```

## 4. Understand the Architecture

**Read these in order:**
1. [UPDATE_SUMMARY.md](docs/UPDATE_SUMMARY.md) - What's new (10 min)
2. [ParserGPT_Comparison.md](docs/ParserGPT_Comparison.md) - Why these changes (15 min)
3. [System Design v2.0](docs/SYSTEM_DESIGN_LLM_Web_Scraper_v2.0.md) - Technical spec (30 min)

**Key Concept:** LLM as "Compiler"
```
Learn Once (Multi-Sample) → Run Fast (XPath) → Fallback Smart (Field-Level)
```

## 5. Implementation Roadmap

### Phase 1 (Weeks 1-4): Core System
Implement v1.0 basics:
- [ ] Console Alerting (30 lines)
- [ ] Local Storage (100 lines)
- [ ] Httpx Fetcher (40 lines)
- [ ] Direct LLM Provider (80 lines)
- [ ] Lxml Extractor (120 lines)
- [ ] ScrapePage use case (150 lines)

**Goal:** Working system end-to-end

### Phase 2 (Weeks 5-8): ParserGPT Enhancements
Add v2.0 sophistication:
- [ ] Multi-sample collection
- [ ] `propose_selectors()` method
- [ ] `extract_fields()` method (field-level fallback)
- [ ] Validation + repair loop
- [ ] Coverage tracking

**Goal:** Production-quality extraction

### Phase 3 (Weeks 9-16): Scale
- [ ] S3 Storage
- [ ] Knock Alerting
- [ ] Playwright Fetcher
- [ ] PocketFlow Provider
- [ ] Orchestration (Prefect/Celery)

**Goal:** 100+ domains at scale

## 6. Key Files to Implement

### Week 1: Simple Adapters
```
scraper/adapters/alerting/console_alerting.py
scraper/adapters/storage/local_storage.py
scraper/adapters/fetchers/httpx_fetcher.py
```

### Week 2: LLM + Extraction
```
scraper/adapters/llm/direct_provider.py
scraper/adapters/extractors/lxml_extractor.py
```

### Week 3: Use Cases
```
scraper/use_cases/scrape_page.py
scraper/config.py  (complete DI Container)
```

### Week 4: Integration
```
scraper/cli.py
tests/e2e/test_full_flow.py
```

## 7. Testing Strategy

```bash
# Run all tests
pytest

# Unit tests only (fast)
pytest tests/unit/ -m unit

# Integration tests
pytest tests/integration/ -m integration

# With coverage
pytest --cov=scraper --cov-report=html
```

## 8. Cost Expectations

### Config Generation (One-Time)
- v1.0: $0.02 per config
- v2.0: $0.14 per config (7x higher, but worth it!)

### Runtime (Per 10k Pages)
- v1.0: ~$15/month
- v2.0: ~$2.35/month
- **Savings: 85%** 🎉

### At Scale (100 Domains)
- v1.0: $18,000/year
- v2.0: $2,820/year
- **Savings: $15,180/year**

## 9. Development Workflow

### Add a New Adapter

1. Create file in appropriate directory
2. Implement port interface
3. Keep <150 lines
4. Add to DI Container (`config.py`)
5. Add tests
6. Update `.env.example` if needed

**Example:**
```python
# scraper/adapters/alerting/console_alerting.py
from scraper.ports.alerting import Alerting

class ConsoleAlerting(Alerting):
    async def send_alert(self, title, message, severity, metadata):
        print(f"[{severity}] {title}: {message}")
```

```python
# scraper/config.py
@property
def alerting(self) -> Alerting:
    if not self._alerting:
        alert_type = os.getenv("ALERTING", "console")
        if alert_type == "console":
            from scraper.adapters.alerting.console_alerting import ConsoleAlerting
            self._alerting = ConsoleAlerting()
    return self._alerting
```

## 10. Next Steps

### Today
1. ✅ Read UPDATE_SUMMARY.md
2. ✅ Setup environment
3. ✅ Review architecture diagrams

### This Week
4. Implement ConsoleAlerting
5. Implement LocalStorage
6. Implement HttpxFetcher
7. Validate DI Container pattern

### Next 2-3 Weeks
8. Implement DirectProvider
9. Implement LxmlExtractor
10. Implement ScrapePage use case
11. Write tests
12. **First real scrape!**

## 11. Resources

### Documentation
- [System Design v2.0](docs/SYSTEM_DESIGN_LLM_Web_Scraper_v2.0.md) - Complete spec
- [ParserGPT Comparison](docs/ParserGPT_Comparison.md) - Detailed analysis
- [ADR-006](docs/adr/ADR-006-ParserGPT-Enhancements.md) - Decision rationale

### External
- uv docs: https://github.com/astral-sh/uv
- Pydantic: https://docs.pydantic.dev
- Anthropic API: https://docs.anthropic.com

## 12. Troubleshooting

### Import Errors
```bash
uv pip install -e .
```

### Tests Failing with NotImplementedError
**This is expected!** Most adapters aren't implemented yet. Start with Phase 1.

### Environment Variables Not Loading
```bash
# Check .env exists
ls -la .env

# Verify python-dotenv installed
uv pip list | grep dotenv
```

## 13. Success Metrics

### Phase 1 (Week 4)
- [ ] First domain scraped successfully
- [ ] All unit tests passing
- [ ] DI Container working
- [ ] Clean Architecture validated

### Phase 2 (Week 8)
- [ ] Config generation achieves 80%+ coverage
- [ ] LLM costs reduced 70%+
- [ ] Field-level fallback working
- [ ] Coverage tracking operational

### Phase 3 (Week 16)
- [ ] 100+ domains configured
- [ ] 10,000+ pages scraped
- [ ] Auto-repair working
- [ ] System maintainable

---

**Ready to build!** Start with Phase 1, Week 1. 🚀

**Questions?** All answers in the docs:
- Architecture? → System Design v2.0
- Why v2.0? → UPDATE_SUMMARY.md
- Comparison? → ParserGPT_Comparison.md
