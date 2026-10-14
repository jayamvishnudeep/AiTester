---
name: cy-ci-configurator
description: >-
  Configures Cypress to run in CI (GitHub Actions, GitLab CI, Jenkins). Use when an SDET says
  "run Cypress in GitHub Actions", "parallelise our Cypress tests", "keep screenshots and
  videos from CI", or "Cypress fails only in the pipeline". Produces a workflow with the
  official cypress-io/github-action, browser selection, app start-up and wait-on, artifacts on
  failure, JUnit reporting and optional parallel runs, with secrets kept in the CI store.
license: MIT
metadata:
  author: AiTester
  pack: cypress
  version: 1.0.0
---

# CY CI Configurator

You get Cypress **running reliably in the pipeline** — app started, browser chosen, evidence
kept on failure, and nothing secret in the repository.

## When to use
- Cypress runs locally but not yet in CI, or CI runs are slow or hard to diagnose.
- Failures in CI cannot be explained because there are no screenshots or videos.

## Workflow
1. **Confirm the run command** — `cypress run` with the browser (`--browser chrome`), the spec
   pattern, and the config or environment to use.
2. **Start the app** — the action's `start` plus `wait-on` for the app URL, or point `baseUrl`
   at a deployed test environment.
3. **Artifacts** — upload `cypress/screenshots` on failure and `cypress/videos` if video is on;
   keep retention short.
4. **Reports** — a JUnit reporter (for example `mocha-junit-reporter`) so CI shows the results.
5. **Parallelism** — split specs across a matrix, or use Cypress Cloud's `--record --parallel`
   if the team has it (the record key goes in the CI secrets).
6. **Secrets** — environment values through `CYPRESS_*` variables from the CI secret store.

## Output shape
```yaml
# .github/workflows/cypress.yml — draft
name: cypress
on: [pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cypress-io/github-action@v6
        with:
          browser: chrome
          start: npm start
          wait-on: 'http://localhost:3000'
        env:
          CYPRESS_PASSWORD: ${{ secrets.CYPRESS_PASSWORD }}
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: cypress-screenshots
          path: cypress/screenshots
```

## Guardrails
- Never commit record keys or passwords; use the CI secret store.
- Check the action and Node versions against the project before adopting this draft.
- When tests pass locally and fail in CI, compare browser, viewport, time zone and data first.
