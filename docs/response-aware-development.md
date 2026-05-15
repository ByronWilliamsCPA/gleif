---
schema_type: common
title: "Response-Aware Development (RAD)"
status: published
owner: core-maintainer
purpose: "Explains the rationale, implementation, and evaluation criteria for the Response-Aware Development system."
tags:
  - documentation
  - development
  - quality
---

## Executive Summary

Response-Aware Development is a systematic approach to identifying and mitigating implicit assumptions in AI-generated code. This document explains the rationale, implementation, and evaluation criteria for the RAD system.

## Problem Statement

### The Hidden Assumption Crisis

AI coding assistants (including Claude) make implicit assumptions that:

- Pass initial testing in development environments
- Work correctly under ideal conditions
- Fail catastrophically in production under load, concurrency, or edge cases

### Common Failure Patterns

1. **Timing Assumptions**: State updates assumed to complete instantly
2. **Resource Availability**: External services assumed always available
3. **Data Integrity**: Input validation assumed handled elsewhere
4. **Concurrency**: Race conditions in async operations
5. **Type Safety**: Runtime type mismatches at boundaries

### Real-World Impact

```python
# This code killed production at 3 AM:
conn = get_connection()
results = conn.execute("SELECT * FROM lei_records WHERE lei = ?", [lei]).fetchall()
# Assumes connection is always valid and table is loaded - WRONG under cold start

# This code survived production:
conn = get_connection()
if conn is None or not table_exists(conn, "lei_records"):
    raise RuntimeError("Database not initialized; run 'gleif load' first")
results = conn.execute("SELECT * FROM lei_records WHERE lei = ?", [lei]).fetchall()
```

## Solution Architecture

### Core Innovation: Context Isolation

The key insight is that **the same context that made an assumption cannot effectively review it**. We need fresh eyes (a different AI context) to spot blind spots.

### Three-Tier Risk Model

We classify assumptions by potential impact and route them to appropriate models:

| Tier | Tag | Risk Level | Model | Use case |
| ---- | --- | ---------- | ----- | -------- |
| 1 | #CRITICAL | Production outages, data loss | Opus 4.7 | Multi-step decisions, deep reasoning |
| 2 | #ASSUME | Functional bugs, UX issues | Sonnet 4.6 | Standard verification, code review |
| 3 | #EDGE | Rare scenarios, optimizations | Haiku 4.5 | Quick lookups, structural checks |

## Implementation Strategy

### Phase 1: Tagging (Current)

- Claude adds assumption tags during code generation
- Developers can manually add tags during review
- Tags include risk level and verification hints

### Phase 2: Verification (Automated)

- Slash command triggers multi-model verification
- Parallel processing for efficiency
- Fresh context prevents confirmation bias

### Phase 3: Remediation (Guided)

- Verification agent generates defensive code
- Fixes applied automatically or via review
- Assumptions marked as verified

## Evaluation Metrics

### Quantitative Metrics

To evaluate effectiveness after 30-60 days:

1. **Assumption Detection Rate**
   - Total assumptions tagged per 1000 lines of code
   - Distribution across risk tiers
   - Most common assumption categories

2. **Fix Application Rate**
   - Percentage of assumptions that needed fixes
   - Percentage of fixes applied vs deferred
   - Time from detection to remediation

3. **Production Impact**
   - Production incidents traced to assumptions
   - Incidents prevented by RAD fixes
   - Mean time to resolution (MTTR) improvement

4. **Cost Efficiency**
   - Average cost per verification
   - Percentage handled by free models
   - ROI: incidents prevented vs verification cost

### Qualitative Metrics

1. **Developer Experience**
   - Ease of understanding tagged assumptions
   - Quality of generated fixes
   - Workflow integration friction

2. **Model Performance**
   - Accuracy of risk classification
   - Quality of fixes by model tier
   - False positive rate

3. **Pattern Recognition**
   - Recurring assumption patterns identified
   - Improvements to initial code generation
   - Knowledge base growth

## Success Criteria

### Short-term (30 days)

- [ ] 80% of critical assumptions caught before production
- [ ] <$0.01 average cost per file verified
- [ ] <2 minute verification time for typical PR

### Medium-term (60 days)

- [ ] 50% reduction in assumption-related production incidents
- [ ] Pattern database with >100 common assumptions
- [ ] Automated fix rate >70% for standard assumptions

### Long-term (90+ days)

- [ ] Claude proactively avoids learned assumption patterns
- [ ] Organization-specific assumption knowledge base
- [ ] Near-zero critical assumptions reaching production

## Risk Mitigation

### Potential Risks and Mitigations

1. **Over-tagging**: Too many trivial assumptions
   - Mitigation: Clear guidelines on what to tag
   - Focus on production-impacting assumptions only

2. **Model Hallucination**: Incorrect fixes from verification
   - Mitigation: Human review for critical fixes
   - Test coverage requirement for all fixes

3. **Performance Impact**: Slow verification blocking commits
   - Mitigation: Parallel processing
   - Async verification for non-critical items

4. **Developer Resistance**: Additional workflow complexity
   - Mitigation: Clear value demonstration
   - Gradual rollout starting with critical only

## Implementation Checklist

### Setup Requirements

- [ ] `CLAUDE.md` updated with RAD tagging standards (see global `~/.claude/CLAUDE.md`)
- [ ] Team members familiar with `#CRITICAL`, `#ASSUME`, `#EDGE` tag semantics
- [ ] Pre-commit hooks configured (optional)

### Verification Points

- [ ] Test with synthetic assumption examples
- [ ] Verify tags are caught during code review
- [ ] Confirm `#VERIFY` instructions are actionable

### Monitoring Setup

- [ ] Assumption tracking database/log
- [ ] Cost monitoring dashboard
- [ ] Incident correlation tracking
- [ ] Developer feedback channel

## Example Workflow

```bash
# 1. Developer codes with Claude
$ claude "implement lei lookup with parent traversal"
# Claude generates code with #CRITICAL/#ASSUME/#EDGE tags and #VERIFY instructions

# 2. Before commit, review tagged assumptions
$ grep -rn '#CRITICAL\|#ASSUME\|#EDGE' src/
# Work through each #VERIFY instruction manually or via PR review

# 3. Commit with assumptions documented
$ git commit -m "feat: lei parent traversal with RAD assumption tags"
```

## Conclusion

Response-Aware Development represents a shift from "hope it works in production" to "verify assumptions systematically". By running multiple AI models with fresh contexts, we can catch subtle issues that single-context development misses.

The tiered approach balances quality and cost: premium models handle critical assumptions while free models cover the bulk of verification work.

Success will be measured by reduced production incidents, improved code quality, and developer confidence in AI-generated code.

---

*Document Version: 1.1*
*Last Updated: 2026-05-14*
