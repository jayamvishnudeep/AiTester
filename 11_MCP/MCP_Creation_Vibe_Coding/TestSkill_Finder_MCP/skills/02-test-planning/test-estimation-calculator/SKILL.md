---
name: test-estimation-calculator
description: >-
  Estimate testing effort for a release, feature or sprint. Use when a QA lead says "how long
  will testing take", "estimate the QA effort", "give me a test estimate for this scope", or
  shares a list of features or stories. Breaks the work into tasks, applies three-point
  (PERT) estimates with stated assumptions, adds visible buffers for retesting and
  environment risk, and shows the arithmetic so the estimate can be challenged. Never
  invents velocity or historical data.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Planning
  version: 1.0.0
---

# Test Estimation Calculator

You produce an **estimate with visible arithmetic and named assumptions** — something a team
can argue with, not a number pulled from the air.

## When to use
- The scope is known (stories, features, test cases) and someone needs QA effort or duration.
- A test plan needs a staffing or timeline section.

## Workflow
1. **Break down the work (WBS)** — per feature: requirement review, test design, test case
   writing, test data, environment setup, execution, regression, retest of fixes, reporting,
   and automation if it is in scope.
2. **Three-point estimate each task** — optimistic (O), most likely (M), pessimistic (P), in
   hours. PERT estimate = (O + 4M + P) / 6; standard deviation = (P − O) / 6.
3. **Use real inputs only** — if the team has past data (hours per test case, defects per
   feature), use it and cite it; otherwise label every figure as an assumption to replace.
4. **Add explicit buffers** — retest and regression cycles (state how many), environment
   downtime, defect-fix turnaround. Each buffer gets its own line.
5. **Convert to calendar time** — divide by people × productive hours per day (state it, for
   example 6 h) and add dependencies such as build drops and environment availability.
6. **Give a range** — total ± one or two standard deviations, not a single number.

## Output shape
```
## Test Estimate — <scope>
| Task | O | M | P | PERT (h) | Note |
|------|---|---|---|----------|------|
| Test design: checkout | 4 | 6 | 10 | 6.3 | assumption: 3 payment methods |
| Execution: checkout | 8 | 12 | 20 | 12.7 | 2 browsers |
...
Subtotal: 84 h · Buffers: retest 2 cycles (+16 h), environment risk (+8 h)
Total: 108 h ± 9 h → 2 testers × 6 h/day ≈ 9 working days
Assumptions to replace with real data: ...
--- HUMAN REVIEW GATE --- "Confirm the assumptions before this estimate is shared"
```

## Guardrails
- Show the formula and the inputs; an estimate without arithmetic cannot be reviewed.
- Never invent historical productivity; mark every figure that is a guess.
- Give a range and its main risks, not false precision.
