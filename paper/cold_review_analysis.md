# Cold Review + Comparable Papers Analysis (2026-03-25)

## Cold Review Scores (Fresh Eyes, No Prior Context)

| Reviewer | Score | Top Criticism |
|----------|-------|---------------|
| Research Scientist | **Weak Reject** | FDR=1.000 tautological, iteration confound, FPR=0.000 suspicious |
| VLDB Judge | **Weak Reject** | No scalability eval, stubs not integrations, hallucination unvalidated |
| Systems Reviewer | **Weak Reject** | "Attribute schema not architecture" — no novel runtime mechanism |
| Senior ML Engineer | **Weak Accept** | Good taxonomy but stubs + no head-to-head vs Langfuse/Datadog |
| AI Safety Researcher | **Weak Reject** | GUARD_RAIL is passive not active, no adversarial robustness |

## Key Comparable Papers (Accepted at Top Venues)

| Paper | Venue | What it has that AgentTelemetry lacks |
|-------|-------|--------------------------------------|
| MAST | NeurIPS 2025 | 1,600+ real traces, multiple annotators, κ=0.88 |
| AGDebugger | CHI 2025 | 14-person user study |
| AgentStepper | arXiv 2026 | 12-person user study, 17%→60% bug detection |
| AgentDiagnose | EMNLP 2025 | Downstream application (training data curation) |
| AIOpsLab | MLSys 2025 | Complete framework (workload gen + fault injection + eval) |
| Dapper/Canopy | Google/SOSP | Production deployment at massive scale |
| GuardAgent | ICML 2025 | Custom safety benchmarks, 98% accuracy |

## Top 3 Gaps vs Accepted Papers

1. **No user study** — AGDebugger (CHI'25) and AgentStepper both have user studies
2. **Synthetic-only fault analysis** — MAST has 1,600+ real traces; we have 14 synthetic types
3. **No production deployment** — Dapper/Canopy/AIOpsLab all have real deployments

## Revised Improvement Plan (Priority Order)

### Tier 1: Must-do for acceptance at any top venue
1. Reframe paper: lead with SWE-bench, not FDR=1.000
2. Fix SWE-bench iteration confound (8-iter matched control)
3. Compute FPR on real traces (SWE-bench + real LLM)
4. Add 2+ real framework E2E tests
5. Scope down safety claims (GUARD_RAIL = observability only)

### Tier 2: Differentiates from Accept to Strong Accept
6. 6-8 person user study (time-to-root-cause with vs without)
7. Head-to-head vs Langfuse/OpenLLMetry on same workload
8. Scalability stress test (concurrent traces, export backpressure)
9. Add novel runtime mechanism (adaptive sampling or circuit breaker)

### Tier 3: Differentiates for best paper consideration
10. Real failure analysis on 100+ agent traces (not synthetic injection)
11. Downstream application (use telemetry for training data curation)
12. File OTEP to get conventions into OTel standard

## Venue Recommendation

Given the cold review consensus and comparable paper landscape:
- **Best fit: ICSE 2027 "AI for SE" track** — values taxonomy + empirical validation
- **Good fit: EMNLP 2027 Demo Track** — tool paper with SWE-bench evaluation
- **Stretch: MLSys 2027** — needs novel systems mechanism (Tier 2 items 8-9)
- **Stretch: NeurIPS D&B** — needs larger real failure dataset (MAST-scale)
