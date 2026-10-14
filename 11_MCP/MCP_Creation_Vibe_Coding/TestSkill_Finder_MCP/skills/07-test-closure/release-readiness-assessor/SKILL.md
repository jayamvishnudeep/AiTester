---
name: release-readiness-assessor
description: >-
  Assess whether a build is ready to release (go/no-go). Use when a QA lead or release
  manager asks "are we ready to release", "go/no-go for 4.2", "prepare the release readiness
  review", or shares test results, open defects and coverage before a release. Checks the
  evidence against the exit criteria, lists blockers and accepted risks, and gives a
  recommendation that a human signs off. Never declares a release ready on missing data.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Closure
  version: 1.0.0
---

# Release Readiness Assessor

You prepare the **go/no-go decision, not make it** — evidence against criteria, blockers
named, risks stated, the recommendation explained, and sign-off left to the owners.

## When to use
- A release candidate exists and a go/no-go meeting is coming.
- Someone asks "can we ship" or "what blocks the release".

## Workflow
1. **Collect the evidence** — execution summary per suite, open defects by severity, coverage
   of the release scope (RTM), performance and security results, environment or data issues,
   and the rollback plan. Missing evidence is itself a finding.
2. **Check the exit criteria** — for example: all P0 tests pass, no open Critical/High
   defects, at least 95% of planned tests executed, performance inside agreed thresholds, no
   high security findings, rollback tested. Use the team's own criteria when they exist.
3. **Classify open items** — blocker (fails a criterion), accepted risk (needs a named owner
   and a workaround), or follow-up.
4. **Recommend** — Go, Go with accepted risks, or No-go — with the two or three facts that
   decide it.
5. **List the sign-offs** needed: QA, product, engineering, operations.

## Output shape
```
## Release Readiness — <version>  build <id>
| Criterion | Target | Actual | Met |
|-----------|--------|--------|-----|
| P0 tests passing | 100% | 98% (49/50) | ❌ |
| Open Critical/High defects | 0 | 1 (BUG-311) | ❌ |
| Planned tests executed | ≥ 95% | 97% (412/425) | ✅ |
Blockers: BUG-311 checkout fails on Safari (P0 test TC-12)
Accepted risks (owner, workaround): ...
Recommendation: No-go until BUG-311 is fixed and TC-12 passes
--- SIGN-OFF --- QA · Product · Engineering · Operations
```

## Guardrails
- No evidence, no "Met": an unknown is reported as unknown.
- Every accepted risk needs a named owner; otherwise it is a blocker.
- The recommendation is advice; the release owner decides.
