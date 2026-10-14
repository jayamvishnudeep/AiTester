---
name: ci-test-pipeline-builder
description: >-
  Design a CI pipeline that runs automated tests as quality gates. Use when a team says "run
  our tests in CI", "set up a test pipeline in GitHub Actions / Jenkins / GitLab CI", "add
  quality gates", or "parallelise our test suite". Produces stages (lint, unit, API,
  end-to-end), sharding, caching, test reports and artifacts, and the rules that block a merge
  or a release. Framework-agnostic; the Playwright and Cypress packs have framework-specific
  CI skills.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Execution
  version: 1.0.0
---

# CI Test Pipeline Builder

You design the **pipeline that turns tests into gates** — fast feedback first, slower suites
later, and clear rules for what blocks a merge or a release.

## When to use
- Tests exist but run only on laptops, or CI is slow, flaky or ignored.
- A team needs merge or release gates based on test results.

## Workflow
1. **Inventory the suites** — unit, API, end-to-end, performance, security scans: run time,
   environment needs, flakiness.
2. **Order the stages by speed** — lint and static checks → unit → API/integration →
   end-to-end (sharded) → nightly long suites (performance, full cross-browser). Fail fast.
3. **Parallelise** — shard end-to-end suites across runners with a matrix, cache dependencies
   and browsers, keep each shard inside the team's time budget.
4. **Report** — JUnit XML for the CI's test view, HTML reports, and screenshots, videos or
   traces as artifacts on failure, with short retention.
5. **Define the gates** — pull request: unit, API and smoke end-to-end must pass; main: full
   end-to-end; release: full regression and no open P0/P1 defects. Retries only for named
   flaky tests, and every retry is logged.
6. **Secrets and environments** — credentials from the CI secret store, never in the repo.

## Output shape
```yaml
# .github/workflows/tests.yml — draft
name: tests
on: [pull_request]
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
  e2e:
    needs: unit
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test --shard=${{ matrix.shard }}/4
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: report-${{ matrix.shard }}
          path: playwright-report/
```
Gates: pull request → unit + smoke e2e · main → full e2e · release → full regression + no open P0/P1

## Guardrails
- Document who may bypass a gate and how; a gate anyone can skip silently is not a gate.
- Never put secrets in pipeline files; use the CI secret store.
- Retries hide bugs: allow them only for named flaky tests and report every retry.
