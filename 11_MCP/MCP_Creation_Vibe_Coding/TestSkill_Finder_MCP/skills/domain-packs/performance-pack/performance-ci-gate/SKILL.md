---
name: performance-ci-gate
description: >-
  Adds automated performance regression checks to CI. Use when a team says "catch
  performance regressions before release", "fail the build if the API gets slower", "add
  Lighthouse to the pipeline", or "run a small load test on every merge". Produces a short,
  repeatable smoke-load stage with thresholds, a baseline comparison with a tolerance for
  noise, front-end budgets, and rules for when a performance failure blocks a merge.
license: MIT
metadata:
  author: AiTester
  pack: performance
  version: 1.0.0
---

# Performance CI Gate

You make performance **a check that runs every day**, small enough to be fast and stable enough
to trust, instead of a big test once before release.

## When to use
- Performance regressions are found late, during release testing or in production.
- Load tests exist but only run manually.

## Workflow
1. **Pick the checks** — a 2-5 minute smoke load on the top transactions (k6, Gatling or JMeter
   in non-GUI mode) and Lighthouse CI on key pages.
2. **Control the noise** — a dedicated or consistent runner, the same environment size, a
   warm-up period excluded from results, and the median of several runs for front-end metrics.
3. **Set thresholds two ways** — absolute limits from the objectives (p95 < 500 ms) and a
   relative limit against the last good baseline (no more than 15% slower).
4. **Store results** — keep each run's summary as an artifact, and the baseline in a known place.
5. **Decide the gate** — fail the build on threshold breaches; warn only on smaller drifts;
   allow overrides only with a reason recorded.
6. **Run the full suite elsewhere** — full load, stress and soak tests stay in nightly or
   pre-release pipelines.

## Output shape
```yaml
# CI stage — draft
perf-smoke:
  needs: deploy-to-perf-env
  steps:
    - run: k6 run --summary-export=perf-summary.json perf/smoke.js   # thresholds fail the job
    - run: python perf/compare_baseline.py perf-summary.json baseline.json --max-regression 15
    - run: npx @lhci/cli autorun --config=lighthouserc.json
  artifacts: [perf-summary.json, .lighthouseci/]
```
Gate: block on threshold breach or > 15% p95 regression · warn on 5-15%

## Guardrails
- Never compare against a baseline from a different environment or data set.
- A flaky gate gets ignored; fix noise before making the gate blocking.
- Keep load modest in CI and never point it at production.
