---
name: cy-intercept-mocker
description: >-
  Stubs, spies on and waits for network calls in Cypress with cy.intercept. Use when an SDET
  says "mock this API in Cypress", "stub the response", "test the error state", "wait for the
  request instead of sleeping", or needs fixtures for backend responses. Produces intercepts
  with fixtures, error and delay simulations, request assertions and aliases — while keeping
  some tests against the real backend so mocks do not hide integration bugs.
license: MIT
metadata:
  author: AiTester
  pack: cypress
  version: 1.0.0
---

# CY Intercept Mocker

You control the network so tests are **fast and can reach error states on purpose**, without
pretending that a mocked happy path proves the integration works.

## When to use
- A UI state depends on a backend response that is hard to produce (empty list, 500, timeout).
- Tests use fixed sleeps or fail when the backend is slow.

## Workflow
1. **Spy or stub** — spy (`cy.intercept(method, url).as('name')`) to wait for and assert on
   real traffic; stub (`cy.intercept(method, url, { fixture | body | statusCode })`) to
   control the response.
2. **Match precisely** — method plus a URL glob or RegExp; a route matcher for query or headers
   when needed. Broad matchers catch unrelated calls.
3. **Fixtures** — realistic payloads in `cypress/fixtures/`, shaped like the real contract.
4. **Error and edge states** — `statusCode: 500`, `forceNetworkError: true`, `delay`, empty
   arrays, the last page of a paginated list.
5. **Assert the request** — `cy.wait('@alias').its('request.body')` for what the UI sent.
6. **Keep a contract check** — at least one non-stubbed test or an API test per stubbed
   endpoint, so the mocks stay honest.

## Output shape
```typescript
it('shows an empty state when there are no orders', () => {
  cy.intercept('GET', '/api/orders*', { statusCode: 200, body: [] }).as('orders');
  cy.visit('/orders');
  cy.wait('@orders');
  cy.get('[data-cy=empty-orders]').should('contain', 'No orders yet');
});

it('offers a retry after a server error', () => {
  cy.intercept('GET', '/api/orders*', { statusCode: 500 }).as('orders');
  cy.visit('/orders');
  cy.wait('@orders');
  cy.get('[data-cy=retry]').should('be.visible');
});
```

## Guardrails
- Fixtures must match the real API contract; never invent fields.
- Register an intercept before the action that triggers the request.
- A suite where every endpoint is stubbed is a UI test, not an end-to-end test; say which it is.
