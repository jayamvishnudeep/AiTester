---
name: traceability-matrix-builder
description: >-
  Build a requirements traceability matrix (RTM). Use when a tester or QA lead says "create
  an RTM", "map requirements to test cases", "which requirements have no tests", or must show
  coverage for an audit or a release. Links each requirement to its test cases, their latest
  results and open defects, and reports uncovered requirements, orphan test cases and failing
  coverage. Uses only the IDs that exist in the inputs.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Case Development
  version: 1.0.0
---

# Traceability Matrix Builder

You make coverage **visible and checkable**: every requirement → its tests → their results →
open defects. The gaps are the main deliverable.

## When to use
- A release, audit or regulated project needs proof of coverage.
- Someone asks "is every requirement tested" or "what does this failing test affect".

## Workflow
1. **Collect the inputs** — requirement list (IDs and titles), test cases with the requirement
   IDs they cover, latest execution results, open defects with their linked tests or
   requirements. If links are missing, ask; do not infer them from similar wording.
2. **Forward traceability** — requirement → test cases → status.
3. **Backward traceability** — test case → requirement. Tests with no requirement are
   "orphans": outdated tests, or a requirement nobody wrote down.
4. **Coverage per requirement** — covered (at least one test), passing (all linked tests pass),
   failing, not run, uncovered. Count and percentage per status.
5. **List the gaps first** — uncovered requirements, requirements whose tests fail or were not
   run, orphan tests, high-severity defects on covered requirements.

## Output shape
```
## RTM — <release>
| Req | Title | Test cases | Last result | Open defects | Status |
|-----|-------|------------|-------------|--------------|--------|
| REQ-12 | Password reset | TC-101, TC-102 | pass, fail | BUG-77 (High) | ⚠️ failing |
| REQ-13 | Lockout after 5 tries | — | — | — | ❌ uncovered |
Coverage: 18/20 covered (90%) · 15 passing · 2 failing · 1 not run
Orphan tests: TC-140 (no requirement)
--- HUMAN REVIEW GATE --- "Confirm the links and decide on the uncovered requirements"
```

## Guardrails
- Never create a link that is not in the inputs; a missing link is a gap.
- Report percentages with their counts (18/20), never alone.
- An uncovered high-risk requirement is a release risk; say so plainly.
