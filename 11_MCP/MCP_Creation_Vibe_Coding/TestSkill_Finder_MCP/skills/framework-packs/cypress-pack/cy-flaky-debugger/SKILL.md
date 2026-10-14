---
name: cy-flaky-debugger
description: >-
  Diagnoses and fixes flaky Cypress tests. Use when an SDET says "this Cypress test fails
  randomly", "passes locally but fails in CI", "element is detached from the DOM", "element
  not found sometimes", or shares a failing run with screenshots or videos. Classifies the
  root cause (fixed waits, detached elements, test interdependence, network timing,
  animations, data collisions) and proposes a specific fix for each — never "just add
  retries".
license: MIT
metadata:
  author: AiTester
  pack: cypress
  version: 1.0.0
---

# CY Flaky Debugger

You find **why** a Cypress test is flaky and fix the cause; retries are a temporary quarantine,
not a fix.

## When to use
- A test fails intermittently, or only in CI.
- Errors such as "element is detached from the DOM", "Timed out retrying", or assertions that
  pass on a rerun.

## Workflow
1. **Collect the evidence** — the error, screenshot or video, the spec, recent changes, and
   whether it fails alone or only in the full run.
2. **Classify the cause:**
   - Fixed waits (`cy.wait(ms)`) racing the app → wait on an `@alias` or an assertion.
   - Detached DOM (element re-rendered after the query) → re-query in the chain, do not keep
     element references, assert before acting.
   - Test interdependence (state from an earlier test) → isolate with `cy.session` and API
     seeding; run the spec alone to confirm.
   - Network timing → `cy.intercept` and wait on the alias before asserting.
   - Animations or overlays → assert the overlay is gone (`should('not.exist')`).
   - Data collisions in parallel CI → unique test data per run.
3. **Propose the fix** with the changed lines and why it removes the race.
4. **Verify** — run the spec many times locally and in CI before lifting any quarantine.

## Output shape
```
## Flaky Test — cypress/e2e/cart.cy.ts › removes an item
Symptom: "cy.click() failed because this element is detached from the DOM" (3 of 20 CI runs)
Cause: the list re-renders after GET /api/cart and the test clicks the old element
Fix:
-  cy.get('[data-cy=item]').first().as('item'); cy.wait(1000); cy.get('@item').click()
+  cy.intercept('GET', '/api/cart').as('cart'); cy.visit('/cart'); cy.wait('@cart')
+  cy.get('[data-cy=item]').first().click()
Verification: 50/50 local runs green; watch the next 20 CI runs
```

## Guardrails
- Retries in the config may quarantine a test, but the report must name the cause.
- Do not raise timeouts globally to hide slowness; fix the specific wait.
- Never mark a test fixed after one green run.
