---
name: risk-based-test-prioritizer
description: >-
  Prioritise features, scenarios or test cases by risk. Use when a tester says "we can't test
  everything, what first", "do risk-based testing", "prioritise these test cases", or shares a
  feature list before a tight release. Scores each item on likelihood of failure and business
  impact, builds a risk matrix, and maps the result to P0/P1/P2 test depth, with the reasons
  visible so the team can adjust the scores.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Planning
  version: 1.0.0
---

# Risk-Based Test Prioritizer

You turn "test everything" into an **explicit, reviewable order of what to test first and how
deeply**. The scores are a proposal the team adjusts, not a verdict.

## When to use
- Time or people are short and the scope cannot all be tested to the same depth.
- A regression or release plan needs a defensible order.

## Workflow
1. **List the items** — features, user journeys or test cases, one per row.
2. **Score likelihood (1-5)** from evidence: code churn, complexity, new technology, defect
   history, number of integrations, team familiarity. Name the evidence.
3. **Score impact (1-5)** — money, users affected, data loss, legal or regulatory exposure,
   reputation, whether a workaround exists.
4. **Risk = likelihood × impact** (1-25). Bands: 15-25 high → P0, 8-14 medium → P1,
   1-7 low → P2.
5. **Set the test depth per band** — P0: positive, negative, boundary and integration tests,
   automated where possible; P1: main paths and key negatives; P2: smoke or exploratory only.
6. **Show the matrix and the cut line** — what will not be tested at all if time runs out.

## Output shape
```
## Risk-Based Priorities — <release>
| Item | Likelihood (why) | Impact (why) | Risk | Priority | Test depth |
|------|------------------|--------------|------|----------|------------|
| Card payment | 4 (new gateway) | 5 (revenue) | 20 | P0 | full + automation |
| Order history | 3 (new filters) | 3 (support load) | 9 | P1 | main paths |
| Profile photo | 2 (unchanged) | 2 (cosmetic) | 4 | P2 | smoke |
Cut line if time runs out: everything below P1
--- HUMAN REVIEW GATE --- "Adjust the scores; the order follows from them"
```

## Guardrails
- Every score needs a stated reason; unexplained numbers are not risk analysis.
- Never drop a legal, security or data-loss item below P1 without saying so explicitly.
- Re-score after major changes; risk is not fixed for the whole release.
