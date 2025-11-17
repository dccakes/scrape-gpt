# ADR-006: ParserGPT-Inspired Enhancements

**Date:** 2025-11-17  
**Status:** Accepted  
**Deciders:** Diego (CTO)  
**Supersedes:** Partial aspects of v1.0 design

## Context

After analyzing ParserGPT's architecture (a production web scraping system), we identified several sophisticated patterns that could significantly improve our system's cost-efficiency, extraction quality, and reliability.

### Current State (v1.0)
Our initial design uses:
- Single-page config generation
- Page-level LLM fallback (re-extract all fields)
- No validation of generated configs
- No coverage tracking

### ParserGPT Insights
ParserGPT demonstrated:
- Multi-sample config generation with 3-5 pages
- Field-level LLM fallback (only missing fields)
- Iterative validation + repair loops
- Coverage statistics tracking

### The Opportunity
We can adopt ParserGPT's sophisticated patterns while **preserving our Clean Architecture advantage** that ParserGPT lacks.

## Decision

We will enhance our v1.0 design with four key ParserGPT-inspired patterns:

### 1. Multi-Sample Config Generation
**Change:** Collect 3-5 sample pages instead of 1 when generating configs.

**Rationale:**
- Selectors tested on multiple pages are more robust
- Captures variation across similar pages
- Reduces false positives (selector works on 1 page by luck)

### 2. Field-Level LLM Fallback
**Change:** Extract only missing fields with LLM, not entire page.

**Rationale:**
- **85% cost reduction** when XPath partially succeeds
- If 9 of 10 fields extracted, only call LLM for 1 field
- Same accuracy, much cheaper

### 3. Validation + Repair Loop
**Change:** Test proposed selectors on samples, repair if coverage < 80%.

**Rationale:**
- Prevents low-quality configs from reaching production
- Iterative improvement produces better selectors
- Automated quality gate

### 4. Coverage Tracking
**Change:** Track per-field success rates over time.

**Rationale:**
- Detect website changes (coverage drops)
- Prioritize which configs need repair
- Measure system health

## Implementation

### Phase 1 (Weeks 1-4): Core System
Build v1.0 as designed - no changes. Get to working MVP.

**Why:** Prove Clean Architecture works, validate core patterns.

### Phase 2 (Weeks 5-8): Add Enhancements
Implement ParserGPT patterns:
- Week 5: Multi-sample collection + `propose_selectors()`
- Week 6: Field-level fallback + `extract_fields()`
- Week 7: Validation loop + `repair_selectors()`
- Week 8: Coverage tracking + monitoring

**Why:** Progressive enhancement, validate each pattern independently.

### Phase 3 (Weeks 9-16): Production Scale
Continue with original roadmap (Prefect, queues, etc.).

## Consequences

### Positive

✅ **85% LLM cost reduction** - Field-level fallback dramatically cheaper  
✅ **Higher config quality** - Multi-sample validation produces robust selectors  
✅ **Observable system health** - Coverage metrics show degradation early  
✅ **Automated quality gates** - Bad configs caught before production  
✅ **Clean Architecture preserved** - All enhancements fit existing ports  
✅ **Gradual adoption** - Can implement incrementally  

### Negative

❌ **Slightly slower config generation** - 3-5 samples vs 1 (acceptable trade-off)  
❌ **More complex use cases** - Validation loops add logic  
❌ **Additional storage** - Coverage stats need persistence  
❌ **Longer Phase 2** - 4 weeks to implement all enhancements  

### Neutral

⚪ **Port interfaces expanded** - New methods, but backward compatible  
⚪ **Testing complexity** - More scenarios to test (but still unit-testable)  

## Comparison: Our System vs ParserGPT

| Aspect | ParserGPT | Our Enhanced System | Winner |
|--------|-----------|---------------------|--------|
| **Config Generation** | Multi-sample with validation | Multi-sample with validation | Tie |
| **LLM Fallback** | Field-level | Field-level | Tie |
| **Cost Efficiency** | Excellent | Excellent | Tie |
| **Clean Architecture** | ❌ Tight coupling | ✅ Ports/Adapters | **Us** |
| **Testability** | ❌ Hard to mock | ✅ Mock any port | **Us** |
| **Flexibility** | ❌ LangChain lock-in | ✅ Swap any provider | **Us** |
| **YAGNI** | ❌ Full stack required | ✅ Progressive complexity | **Us** |
| **Production Ready** | ✅ Proven at scale | ⚠️ To be proven | ParserGPT |

**Verdict:** We get ParserGPT's sophistication + Clean Architecture's maintainability.

## Technical Details

### Enhanced LLMProvider Port

```python
class LLMProvider(ABC):
    # Existing method
    async def generate_structured(...) -> T: pass
    
    # NEW: Multi-sample config generation
    async def propose_selectors(
        samples: List[PageSample],
        schema: Dict[str, Any],
        domain_context: str
    ) -> PageTypeConfig: pass
    
    # NEW: Targeted repairs
    async def repair_selectors(
        current_config: PageTypeConfig,
        failures: List[FieldFailure],
        samples: List[PageSample]
    ) -> PageTypeConfig: pass
    
    # NEW: Field-level extraction
    async def extract_fields(
        html: str,
        fields_to_extract: List[str],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]: pass
```

### Coverage Tracking Schema

```python
# Local storage: coverage-stats/hospital.com/team_page.json
{
  "name": {
    "successes": 980,
    "total": 1000
  },
  "email": {
    "successes": 720,  # 72% - needs repair!
    "total": 1000
  },
  "phone": {
    "successes": 880,
    "total": 1000
  }
}
```

### Cost Calculation

**Scenario:** 1000 pages, 85% XPath success, 10 fields each

**v1.0 (Page-level):**
```
LLM fallback: 150 pages × 10 fields = 1500 field extractions
Cost: 1500 × $0.001 = $15
```

**v2.0 (Field-level):**
```
Partial success: 150 pages × 8.5 fields via XPath = 1275 fields free
LLM fallback: 150 pages × 1.5 fields = 225 field extractions
Cost: 225 × $0.001 = $2.25
```

**Savings: $12.75 per 1000 pages (85% reduction)**

## Alternatives Considered

### Alternative 1: Keep v1.0 Simple Approach

**Pros:**
- Faster to implement
- Simpler code
- Proven to work

**Cons:**
- 6x higher LLM costs
- Lower config quality
- No observability
- Website changes undetected

**Why Rejected:** Cost savings justify complexity.

### Alternative 2: Copy ParserGPT's Full Stack

**Pros:**
- Proven production patterns
- Well-tested approach
- Feature parity

**Cons:**
- Tight LangChain coupling
- No Clean Architecture
- All-or-nothing deployment
- Hard to test/modify

**Why Rejected:** Lose maintainability advantages.

### Alternative 3: Wait for Production Issues

**Pros:**
- Build only what's proven necessary
- Pure YAGNI approach

**Cons:**
- Miss cost optimization window
- Accumulate technical debt
- Reactive rather than proactive

**Why Rejected:** ParserGPT proves patterns work.

## Migration Path

### For New Implementations
Follow Phase 1 → 2 → 3 roadmap in System Design v2.0.

### For Existing v1.0 Implementations
1. Add new methods to `LLMProvider` port
2. Implement in `DirectProvider` / `PocketFlowProvider`
3. Update `ExtractWithFallback` use case
4. Add coverage tracking to `Storage` implementations
5. Optional: Keep v1.0 behavior as fallback

All existing v1.0 code continues working - enhancements are additive.

## Success Metrics

We'll know this decision was correct when:

**Short-term (Month 1):**
- [ ] Config generation produces 80%+ coverage
- [ ] Field-level fallback implemented
- [ ] Unit tests pass with new patterns

**Medium-term (Month 3):**
- [ ] 70%+ LLM cost reduction measured
- [ ] Coverage tracking operational
- [ ] Zero low-quality configs in production

**Long-term (Month 6):**
- [ ] Auto-repair triggered on coverage drops
- [ ] 1000+ pages scraped successfully
- [ ] System maintainability validated

## Risks and Mitigations

### Risk 1: Implementation Complexity
**Mitigation:** Phase 2 is 4 weeks with clear milestones. Can pause if needed.

### Risk 2: Multi-Sample Collection Difficulty
**Mitigation:** Allow manual sample URL provision. Auto-discovery is Phase 3.

### Risk 3: Coverage Stats Storage Growth
**Mitigation:** Aggregate to hourly/daily after initial period.

### Risk 4: Validation Loop Slowness
**Mitigation:** Cap iterations at 3. Accept 70% coverage if needed.

## References

- [ParserGPT Medium Article](https://medium.com/@ayush.shrivastava016/parsergpt-public-beta-coming-soon-turn-messy-websites-into-clean-csvs-dd8c7199ca97)
- [System Design v2.0](../SYSTEM_DESIGN_LLM_Web_Scraper_v2.0.md)
- [ADR-001: Clean Architecture](001-clean-architecture.md)

## Related ADRs

- [ADR-001: Clean Architecture](001-clean-architecture.md) - Foundation preserved
- [ADR-002: PocketFlow (TBD)](002-pocketflow-llm.md) - Will need updates
- [ADR-003: XPath-First (TBD)](003-xpath-first-llm-fallback.md) - Enhanced approach

---

**Approved:** Diego (CTO)  
**Effective Date:** November 17, 2025  
**Review Date:** After Phase 2 completion (Week 8)
