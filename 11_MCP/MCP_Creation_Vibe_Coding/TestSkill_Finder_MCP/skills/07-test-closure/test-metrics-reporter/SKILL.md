---
name: test-metrics-reporter
description: >-
  Calculate and explain test metrics from real execution and defect data. Use when a QA lead
  says "give me the test metrics", "calculate defect density, DRE or leakage", "build a QA
  dashboard", or shares test results and defect exports. Computes execution progress, pass
  rate, defect density, defect removal efficiency, defect leakage, automation coverage and
  flaky rate, shows each formula with its inputs, and explains the trend. Never fills in a
  metric without data.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Closure
  version: 1.0.0
---

# Test Metrics Reporter

You turn raw results into **metrics people can trust**: every number shows its formula and
inputs, and a missing input gives "not available", never an estimate.

## When to use
- A sprint, cycle or release report needs QA metrics.
- Someone wants a dashboard, or wants to know what a metric means.

## Workflow
1. **Collect the inputs** — planned, executed, passed, failed and blocked test counts; defects
   found in testing and after release (with severity and phase); a size measure (KLOC, story
   points or features); automated versus total test cases; tests that passed only on retry.
2. **Compute with stated formulas:**
   - Execution progress = executed / planned
   - Pass rate = passed / executed
   - Defect density = defects / size (state the unit)
   - Defect removal efficiency (DRE) = defects found before release / (before + after release)
   - Defect leakage = defects found after release / total defects
   - Automation coverage = automated test cases / test cases meant to be automated
   - Flaky rate = tests that passed only on retry / tests run
3. **Show trends**, not single values — compare with the previous cycle when data exists.
4. **Explain what each number means** and what action it suggests, and warn against misuse
   (a pass rate alone says nothing about coverage).

## Output shape
```
## Test Metrics — <cycle>
| Metric | Formula | Inputs | Value | Trend |
|--------|---------|--------|-------|-------|
| Pass rate | passed / executed | 412 / 450 | 91.6% | up from 88.0% |
| DRE | before / (before + after) | 57 / (57 + 3) | 95.0% | — |
| Defect leakage | after / total | 3 / 60 | 5.0% | — |
| Flaky rate | retry-only passes / runs | not available | — | — |
What this means: ...
--- HUMAN REVIEW GATE --- "Confirm the inputs before the report is shared"
```

## Guardrails
- Never estimate a missing input; report the metric as not available.
- Always show the counts next to a percentage.
- Metrics describe the process; never use them to rank individual testers.
