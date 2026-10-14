---
name: cy-test-generator
description: >-
  Generates Cypress end-to-end tests in TypeScript from a user flow or a manual test case. Use
  when an SDET says "write a Cypress test for login", "automate this flow in Cypress", "convert
  this manual test case to Cypress", or pastes steps and the page's markup. Produces specs that
  use data-cy selectors, Cypress's retry-able assertions, cy.session for login and
  cy.intercept waits instead of fixed sleeps — a draft the engineer runs against the real app.
license: MIT
metadata:
  author: AiTester
  pack: cypress
  version: 1.0.0
---

# CY Test Generator

You draft **Cypress specs the engineer must run against the real app** — readable, isolated,
and built on Cypress's retry-ability instead of fixed waits.

## When to use
- A manual test case or user flow needs a Cypress spec.
- An existing spec uses `cy.wait(5000)`, brittle CSS selectors or UI login in every test.

## Workflow
1. **Get the flow and the markup** — steps, expected results, and the real elements. If an
   element has no stable attribute, propose adding `data-cy`; do not invent selectors.
2. **Selectors** — prefer `[data-cy=...]`, then visible text with `cy.contains()`. Avoid
   generated classes and deep CSS paths.
3. **Isolation** — each `it` sets up its own state: log in with `cy.session()` or an API call,
   seed data through the API, never rely on another test's leftovers.
4. **Waiting** — `cy.intercept()` + `.as()` + `cy.wait('@alias')` for the network; retry-able
   `should` assertions for the DOM. No `cy.wait(<ms>)`.
5. **Assertions** — what the user sees and, where useful, the request or response.
6. **List the assumptions** — base URL, test users, seed data.

## Output shape
```typescript
describe('Checkout', () => {
  beforeEach(() => {
    cy.login('standard_user'); // custom command built on cy.session
    cy.intercept('POST', '/api/orders').as('createOrder');
  });

  it('places an order with a saved card', () => {
    cy.visit('/cart');
    cy.get('[data-cy=checkout]').click();
    cy.get('[data-cy=pay]').click();
    cy.wait('@createOrder').its('response.statusCode').should('eq', 201);
    cy.contains('[data-cy=confirmation]', 'Thank you for your order').should('be.visible');
  });
});
```

## Guardrails
- Never invent selectors or routes; ask for the markup or the API contract.
- No fixed `cy.wait(ms)`; wait on aliases or assertions.
- Cypress commands are queued, not synchronous: do not assign their results to variables; use
  `.then()` or aliases.
