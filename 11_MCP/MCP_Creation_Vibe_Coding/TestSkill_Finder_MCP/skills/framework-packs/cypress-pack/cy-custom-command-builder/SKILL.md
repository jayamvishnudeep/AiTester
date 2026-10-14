---
name: cy-custom-command-builder
description: >-
  Builds reusable Cypress custom commands with TypeScript types. Use when an SDET says
  "create a cy.login command", "stop repeating these steps", "add a custom command", or "cache
  login with cy.session". Produces commands in cypress/support/commands.ts with type
  declarations, API-based login cached by cy.session, and guidance on when a plain helper
  function is the better choice.
license: MIT
metadata:
  author: AiTester
  pack: cypress
  version: 1.0.0
---

# CY Custom Command Builder

You turn repeated steps into **small, typed, well-named commands** — and say when a plain
function would be simpler.

## When to use
- The same setup (login, seeding, navigation) is copied across specs.
- Logging in through the UI makes every test slow.

## Workflow
1. **Find the repetition** — steps repeated in three or more specs are candidates.
2. **Prefer the API for setup** — log in with `cy.request()` and cache it with
   `cy.session(id, setup, { validate })`; seed data through the API.
3. **Write the command** in `cypress/support/commands.ts` with `Cypress.Commands.add`.
   Commands that act on an element use `{ prevSubject: 'element' }`.
4. **Type it** — extend `Cypress.Chainable` in a `declare global` block so editors autocomplete.
5. **Keep commands small** — one purpose each, and no hidden assertions unless the name says so
   (for example `assertToast`).
6. **Document** each command with a one-line usage example.

## Output shape
```typescript
// cypress/support/commands.ts
Cypress.Commands.add('login', (user: string) => {
  cy.session(user, () => {
    cy.request('POST', '/api/login', { username: user, password: Cypress.env('PASSWORD') })
      .its('status').should('eq', 200);
  }, {
    validate: () => { cy.getCookie('session').should('exist'); },
  });
});

declare global {
  namespace Cypress {
    interface Chainable {
      login(user: string): Chainable<void>;
    }
  }
}
export {};
```

## Guardrails
- Never hard-code passwords; read them from `Cypress.env` filled by the CI secret store.
- Setup commands should fail loudly: a broken login must fail in setup, not three steps later.
- If a helper does not need the command chain, a plain function is clearer than a command.
