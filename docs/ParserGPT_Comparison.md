# ParserGPT vs Our System: Detailed Comparison

**Date:** November 17, 2025  
**Purpose:** Document analysis of ParserGPT and how we incorporate its strengths

---

## Executive Summary

**ParserGPT** is a production-proven web scraping system with sophisticated extraction patterns.  
**Our System** adopts ParserGPT's best patterns while maintaining Clean Architecture advantages.

**Result:** Best-of-both-worlds approach combining extraction sophistication with long-term maintainability.

---

## Side-by-Side Comparison

### Architecture

| Aspect | ParserGPT | Our System Enhanced |
|--------|-----------|---------------------|
| **Overall Pattern** | Learner + Runner | Config Generation + Scraping |
| **Core Philosophy** | "Compiler" - LLM writes selectors | ✅ Same - "Compiler" approach |
| **Layers** | Monolithic (FastAPI + LangChain + LangGraph) | Clean Architecture (4 layers) |
| **Coupling** | Tight (LangChain dependency throughout) | Loose (ports/adapters pattern) |
| **Testability** | Hard (real LLMs, DB needed) | Easy (mock any port) |
| **Swappability** | Difficult (refactoring required) | Trivial (.env change) |

**Winner:** **Our System** (maintainability) + ParserGPT's patterns (functionality)

---

### Config Generation

| Aspect | ParserGPT | Our System v1.0 | Our System v2.0 |
|--------|-----------|-----------------|-----------------|
| **Sample Count** | 3-5 pages | 1 page | ✅ 3-5 pages |
| **Validation** | Yes (test on samples) | No | ✅ Yes |
| **Repair Loop** | Yes (iterate until good) | No | ✅ Yes |
| **Quality Gate** | Coverage threshold | None | ✅ 80% coverage |
| **Output** | adapter.json | config.json | ✅ validated config |

**Evolution:** v1.0 → v2.0 adopts ParserGPT's quality approach

---

### LLM Fallback Strategy

| Aspect | ParserGPT | Our System v1.0 | Our System v2.0 |
|--------|-----------|-----------------|-----------------|
| **Fallback Scope** | Field-level | Page-level | ✅ Field-level |
| **Cost Efficiency** | Excellent | Baseline | ✅ Excellent (85% savings) |
| **Example** | Missing 1 field → extract 1 | Missing 1 field → extract 10 | ✅ Missing 1 field → extract 1 |

**Key Insight:** ParserGPT's field-level approach is 10x more cost-efficient.

**Example Scenario:**
```
Page has 10 fields, XPath extracted 9 successfully, 1 missing (email)

ParserGPT / Our v2.0:
- LLM extracts only "email" field
- Cost: ~$0.001 per page

Our v1.0:
- LLM re-extracts all 10 fields
- Cost: ~$0.010 per page

Savings: 90% in this scenario!
```

---

### Orchestration

| Aspect | ParserGPT | Our System |
|--------|-----------|------------|
| **State Machine** | LangGraph (propose → validate → repair) | Simple Python use cases |
| **Job Queue** | FastAPI async tasks | Phase 3: Celery + Redis |
| **Complexity** | Higher (LangGraph framework) | Lower (YAGNI - build when needed) |
| **Debugging** | Complex (state machine) | Simple (linear flow) |

**Winner:** **Tie** - ParserGPT production-ready now, we build progressively

---

### Storage

| Aspect | ParserGPT | Our System |
|--------|-----------|------------|
| **Primary Storage** | Postgres | Local → S3 (configurable) |
| **Raw HTML** | Postgres BLOBs | Filesystem/S3 |
| **Extracted Data** | Postgres JSON | JSON files or S3 |
| **Configs** | JSON files | JSON files (versioned) |
| **Flexibility** | Low (Postgres only) | High (swap via .env) |
| **Cost** | Higher (DB storage) | Lower (blob storage) |

**Winner:** **Our System** (flexibility, cost)

---

### Coverage Tracking

| Aspect | ParserGPT | Our System v1.0 | Our System v2.0 |
|--------|-----------|-----------------|-----------------|
| **Per-Field Stats** | Not mentioned | No | ✅ Yes |
| **Success Rates** | Not mentioned | No | ✅ Yes |
| **Degradation Detection** | Not mentioned | No | ✅ Yes |
| **Auto-Repair Trigger** | Not mentioned | No | ✅ Phase 2 |

**Evolution:** v2.0 adds this critical observability layer

---

## Code Comparison

### Config Generation

**ParserGPT:**
```python
# Tightly coupled to LangChain
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

parser = PydanticOutputParser(pydantic_object=AdapterDraft)
PROMPT = ChatPromptTemplate.from_messages([...])
llm = ChatOpenAI(model="gpt-4o-mini")

async def propose_adapter(fields, samples):
    return await (PROMPT | llm | parser).ainvoke(msg)
```

**Our System v2.0:**
```python
# Loosely coupled via port
class GenerateConfig:
    def __init__(self, llm: LLMProvider, ...):  # Port!
        self.llm = llm  # Could be any implementation
    
    async def execute(self, ...):
        config = await self.llm.propose_selectors(samples, schema)
        # LLM implementation hidden behind port
```

**Key Difference:** We can swap LLM providers via .env with zero code changes.

---

### Field-Level Fallback

**ParserGPT:**
```python
# Extract only missing fields
llm_row = await llm_fill(url, html)
r = det.copy()
for k, v in llm_row.dict().items():
    if k in prefer and v:
        r[k] = v
```

**Our System v2.0:**
```python
# Same pattern!
missing_fields = ["email", "phone"]
llm_result = await self.llm.extract_fields(
    html=html,
    fields_to_extract=missing_fields
)
merged = merge_results(xpath_result, llm_result)
```

**Similarity:** We adopted this exact pattern.

---

## What We Adopted from ParserGPT

### ✅ 1. Multi-Sample Config Generation
**Why:** More robust selectors, catches edge cases early.

**Impact:** 
- Higher quality configs
- Fewer production failures
- Worth 5x cost of generation (amortized across thousands of pages)

### ✅ 2. Field-Level LLM Fallback
**Why:** 85% cost reduction when XPath partially succeeds.

**Impact:**
- Dramatically cheaper at scale
- Same accuracy
- No downside

### ✅ 3. Validation + Repair Loop
**Why:** Quality gate prevents bad configs from reaching production.

**Impact:**
- Automated quality assurance
- Iterative improvement
- Measurable coverage metrics

### ✅ 4. Coverage Tracking
**Why:** Detect website changes, trigger repairs proactively.

**Impact:**
- Observable system health
- Early warning system
- Data-driven maintenance

---

## What We Keep from Our Design

### ✅ 1. Clean Architecture
**Why:** Long-term maintainability, testability, flexibility.

**ParserGPT's Issue:**
```python
# Can't easily swap LangChain for something else
# Can't mock LLM for fast unit tests
# Postgres is hardcoded throughout
```

**Our Advantage:**
```python
# Swap LLM provider: change .env
# Mock LLM port: fast tests
# Swap storage: change .env
```

### ✅ 2. YAGNI Approach
**Why:** Build only what's needed, when needed.

**ParserGPT:** Requires full stack (FastAPI + Postgres + LangGraph) from day 1.

**Our Approach:**
- Phase 1: Simple adapters (httpx, local storage)
- Phase 2: Add sophistication (Playwright, S3)
- Phase 3: Add orchestration (Prefect, queues)

### ✅ 3. Progressive Complexity
**Why:** Lower barrier to entry, faster MVP.

**Timeline to Working System:**
- ParserGPT: Must build entire stack (2-3 weeks)
- Our System: Working in 1 week, sophisticated in 8 weeks

### ✅ 4. Storage Flexibility
**Why:** Different needs for development vs production.

**ParserGPT:** Postgres only (setup required).

**Our System:**
- Development: Local filesystem (zero setup)
- Production: S3 (scalable, cheap)
- Could add: Postgres, MongoDB, etc. (just another adapter)

---

## Cost Analysis

### Scenario: 10,000 Pages Per Month

**Assumptions:**
- 10 fields per page
- 85% XPath success rate
- LLM cost: $0.001 per field extraction

#### ParserGPT
```
Config generation: 1 domain × 5 samples × $0.02 = $0.10
Runtime extractions:
  - XPath success: 8,500 pages × $0 = $0
  - Field-level LLM: 1,500 pages × 1.5 fields × $0.001 = $2.25
Total: $2.35/month
```

#### Our System v1.0 (Page-Level Fallback)
```
Config generation: 1 domain × 1 sample × $0.02 = $0.02
Runtime extractions:
  - XPath success: 8,500 pages × $0 = $0
  - Page-level LLM: 1,500 pages × 10 fields × $0.001 = $15.00
Total: $15.02/month
```

#### Our System v2.0 (Field-Level Fallback)
```
Config generation: 1 domain × 5 samples × $0.02 = $0.10
Runtime extractions:
  - XPath success: 8,500 pages × $0 = $0
  - Field-level LLM: 1,500 pages × 1.5 fields × $0.001 = $2.25
Total: $2.35/month
```

**Savings: v2.0 vs v1.0 = $12.67/month per domain (84% reduction)**

**At Scale (100 domains):**
- v1.0: $1,500/month
- v2.0: $235/month
- **Savings: $1,265/month** 🎉

---

## Quality Comparison

| Metric | ParserGPT | Our v1.0 | Our v2.0 |
|--------|-----------|----------|----------|
| **Config Reliability** | High (validated) | Unknown | ✅ High (validated) |
| **Runtime Accuracy** | High | High | ✅ High |
| **Cost Efficiency** | Excellent | Poor | ✅ Excellent |
| **Testability** | Low | High | ✅ High |
| **Maintainability** | Medium | High | ✅ High |
| **Observability** | Medium | Low | ✅ High |
| **Flexibility** | Low | High | ✅ High |

---

## Developer Experience

### ParserGPT
```python
# Start new project
1. Setup Postgres
2. Install LangChain, LangGraph
3. Setup FastAPI
4. Write state machine
5. Deploy
Time: 2-3 days
```

### Our System
```python
# Start new project
1. uv venv && uv pip install -e .
2. cp .env.example .env
3. Add API keys
4. python -m scraper.cli scrape https://example.com
Time: 5 minutes
```

**Winner:** **Our System** (YAGNI pays off in dev velocity)

---

## Production Readiness

| Aspect | ParserGPT | Our v1.0 | Our v2.0 |
|--------|-----------|----------|----------|
| **Job Queue** | ✅ Built-in | ❌ Phase 3 | ❌ Phase 3 |
| **API** | ✅ FastAPI | ❌ Phase 3 | ❌ Phase 3 |
| **Storage** | ✅ Postgres | ⚠️ Local only | ✅ S3 option |
| **Monitoring** | ⚠️ Basic | ❌ Phase 3 | ✅ Coverage tracking |
| **Cost Optimization** | ✅ Field-level | ❌ Page-level | ✅ Field-level |
| **Config Quality** | ✅ Validated | ❌ Not validated | ✅ Validated |

**Current State:** ParserGPT more production-ready today.  
**Future State (Week 8):** Our v2.0 at parity or better.

---

## Decision Matrix

### When to Choose ParserGPT Approach
- ✅ Need production system immediately
- ✅ LangChain is acceptable dependency
- ✅ Postgres is preferred storage
- ✅ Single deployment model
- ❌ Don't need to swap providers
- ❌ Don't need extensive testing

### When to Choose Our Approach
- ✅ Building for long-term (1+ years)
- ✅ Want provider flexibility
- ✅ Need extensive testing
- ✅ Progressive deployment
- ✅ YAGNI principles important
- ✅ Multiple teams/contributors
- ❌ Can wait 8 weeks for full sophistication

---

## Our Strategy: Best of Both

### Phase 1 (Weeks 1-4): Prove Architecture
- Build v1.0 with Clean Architecture
- Validate ports/adapters pattern
- Get to working system
- **No ParserGPT patterns yet** (YAGNI)

### Phase 2 (Weeks 5-8): Add Sophistication
- Multi-sample config generation
- Field-level LLM fallback
- Validation + repair loop
- Coverage tracking
- **Adopt all ParserGPT patterns**

### Phase 3 (Weeks 9-16): Scale to Production
- Job queues (Celery)
- API (FastAPI)
- Prefect orchestration
- Advanced monitoring

**Result:** ParserGPT's sophistication + Clean Architecture's maintainability.

---

## Lessons Learned

### From ParserGPT
1. **Multi-sample validation is critical** - One sample is not enough
2. **Field-level fallback saves 85% costs** - Obvious in hindsight
3. **Iterative repair works** - Don't accept first config
4. **Coverage tracking enables proactive maintenance** - Detect changes early

### From Our Design
1. **Clean Architecture pays off long-term** - Flexibility matters
2. **YAGNI enables faster MVP** - Build when needed
3. **Testability requires loose coupling** - Ports/adapters enable mocks
4. **Progressive complexity reduces risk** - Validate architecture early

---

## Recommendation

**Adopt v2.0 Enhanced Design:**

✅ **Keep:** Clean Architecture, YAGNI, DI Container  
✅ **Add:** ParserGPT's extraction patterns  
✅ **Timeline:** Phase 1 (4 weeks) → Phase 2 (4 weeks) → Phase 3 (8 weeks)  
✅ **Result:** Best-of-both-worlds system

**Why This Works:**
- Proven patterns (ParserGPT shows they work)
- Maintainable structure (Clean Architecture)
- Progressive investment (YAGNI)
- Clear roadmap (phased approach)

---

## Conclusion

**ParserGPT** taught us:
- How to generate high-quality configs
- How to minimize LLM costs
- How to track extraction health

**Our design** provides:
- Long-term maintainability
- Testing flexibility
- Provider independence
- Progressive complexity

**Together:** World-class web scraping system! 🚀

---

**Next Steps:**
1. ✅ Review System Design v2.0
2. ✅ Review ADR-006
3. Start Phase 1 implementation (Weeks 1-4)
4. Add Phase 2 enhancements (Weeks 5-8)
5. Scale to production (Weeks 9-16)

**You're ready to build!**
