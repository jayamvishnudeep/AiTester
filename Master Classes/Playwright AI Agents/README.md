# Playwright AI Agents — TTACart End-to-End Suite

A Playwright + TypeScript suite covering [TTACart](https://app.thetestingacademy.com/playwright/ttacart/),
a storefront demo, built with **three Playwright AI agents** rather than by hand.

| | |
|---|---|
| **Application under test** | `https://app.thetestingacademy.com/playwright/ttacart/` |
| **Suite** | 34 tests — 33 scenarios + the generator's seed |
| **Written by** | `playwright-test-planner`, `playwright-test-generator`, `playwright-test-healer` |
| **Built with** | Playwright 1.63, TypeScript 5.7, the `playwright-test` MCP server |
| **Suspected bugs pinned** | 6 |
| **Structure** | Page Object Model, composable state fixtures, area-organised specs |

---

## The three agents that wrote this

Every test here was produced by an AI agent that **drove a real browser first**.
Nothing was written from memory of how storefronts usually behave, and that is the
single most important fact about this suite.

| Agent | What it did |
|---|---|
| **`playwright-test-planner`** | **Explored the live website** with Playwright browser tools — clicked through every page, read every selector, price, tax figure and error string off the running application — and produced [`specs/ttacart-e2e-order-plan.md`](specs/ttacart-e2e-order-plan.md): 613 lines, 24 scenarios, plus appendices recording how all six documented usernames behave and two suspected application bugs it found while exploring |
| **`playwright-test-generator`** | Turned that plan into specs, **executing each step live in the browser before writing the assertion for it**. It ran the click, read what came back, and wrote the expectation from the observation — not the other way round. Its seed file is [`src/tests/seed.spec.ts`](src/tests/seed.spec.ts) |
| **`playwright-test-healer`** | Repairs failures: runs the suite, investigates each failure **against the live page**, and fixes selectors, assertions and timing until it passes — without weakening what the test claims |

### Why that matters more than it sounds

The usual failure of an AI-written test suite is not that it is wrong. It is that
it is **plausible**. Ask a model to write Playwright tests for a storefront and it
will produce `Sauce Labs Backpack` at `$29.99`, a
`getByRole('button', { name: 'Checkout' })` locator, and an assertion that the
cart badge is hidden when the cart is empty.

All three are correct for saucedemo.com. All three are **wrong here**. And none of
them look wrong.

The planner found the real first product is `Test.allTheThings() T-Shirt (Red)` at
`$15.99` — it sorts ahead of the five `TTA …` items because the locale comparison
puts `Te` before `TT`. It found Checkout is an **anchor**, so the role locator
finds nothing. It found the badge is **removed from the DOM** when empty, not
hidden. A model writing from intuition gets all three wrong and the suite still
goes green on the happy path.

That is why the plan runs 613 lines for 24 scenarios. Most of it is reference data,
and the reference data is what makes the rest trustworthy.

**Do not write or repair specs here by hand.** Use the planner for planning, the
generator for writing, the healer for fixing.

---

## Contents

| Path | What it is |
|---|---|
| `specs/ttacart-e2e-order-plan.md` | The planner's test plan — 24 scenarios, the authoritative document |
| `specs/ttacart-extended-negative-plan.md` | Addendum: 9 more scenarios and the four bugs they found |
| `src/tests/` | Specs, organised by area — see below |
| `src/pages/` | One class per page, plus `BasePage` for the shared header shell |
| `src/fixtures/test-base.ts` | The `test`/`expect` specs import: page objects, composable state, storage reset |
| `src/config/` | `env.ts` (typed environment readers) and `credentials.ts` |
| `src/testdata/` | Every verified value — URLs, prices, verbatim error strings |
| `src/utils/` | `UtilElementLocator`, `logger`, `visualStep` |
| `plan.md` | Why it is built this way |

```
src/
├── config/          env.ts · credentials.ts
├── fixtures/        test-base.ts
├── pages/           BasePage · Login · Inventory · Cart
│                    CheckoutInformation · CheckoutOverview · CheckoutComplete
├── testdata/        ttacart.data.ts · logintestdata.json
├── utils/           UtilElementLocator.ts · logger.ts · visualStep.ts
└── tests/
    ├── cart/        cart.spec.ts
    ├── checkout/    checkout-information · checkout-overview · checkout-known-bugs
    ├── e2e/         e2e-checkout.spec.ts
    ├── inventory/   inventory.spec.ts
    ├── login/       login.spec.ts · login-negative.spec.ts
    ├── session/     session.spec.ts
    └── seed.spec.ts
```

---

## Requirements

- **Node.js 20+** (developed on v24)
- **A `.env` file** — see setup
- The `playwright-test` **MCP server**, only to re-run the agents. The committed
  suite runs without it.

---

## Setup

**1. Install.**

```bash
npm install
npx playwright install chromium
```

**2. Create `.env`** by copying [`.env.example`](.env.example) and filling in the
password.

```ini
BASE_URL=https://app.thetestingacademy.com/playwright/ttacart/
TTA_USERNAME=standard_user
TTA_PASSWORD=<the demo password>
```

The `TTA_` prefix is not decoration. Windows defines `USERNAME` as a system
environment variable, and `dotenv` **will not overwrite a variable that is already
set** — so a bare `USERNAME=` key is read, ignored, and your Windows account name
is submitted to the login form instead. `dotenv` considers declining to overwrite
correct behaviour and says nothing, so it surfaces as an auth failure against a
username nobody configured. `.env` is gitignored; never hardcode credentials.

**3. Open *this folder* as the workspace root** if you intend to use the agents —
not the repository root. See troubleshooting.

---

## Usage

```bash
npm run test:headed      # the whole suite, visible
npm test                 # headless
npm run test:smoke       # just the @p0 tagged tests
npm run test:bugs        # only the pinned-bug specs
npm run test:ui          # pick and step through interactively
npm run report           # the HTML report from the last run
npm run typecheck        # tsc --noEmit
npm run lint             # ESLint, type-aware
npm run verify           # typecheck + lint + test
```

```
34 passed (1.3m)
```

### How a spec is put together

Specs import `test` and `expect` from `@fixtures/test-base`, **never from
`@playwright/test` directly** — that import is what supplies the page objects and
the storage reset. State fixtures compose, so a test names the state it needs and
says nothing about how to get there:

```
loggedIn  →  cartWithItem  →  atCheckoutInformation  →  atCheckoutOverview
```

```ts
test('Last Name left blank is rejected', async ({
  atCheckoutInformation,
  checkoutInformationPage,
}) => {
  void atCheckoutInformation;
  await checkoutInformationPage.fillDetails('John', '', '12345');
  await checkoutInformationPage.continue();
  await checkoutInformationPage.expectError(ERRORS.lastNameRequired);
});
```

Page objects hold locators (`private readonly`, exposed through getters) and
actions. Their `expect*` helpers cover only page **identity** and **shell state**
— `expectLoaded`, `expectCartBadgeAbsent`. Everything a scenario specifically
claims stays in the spec, where a reader can see what the test asserts.

Path aliases: `@pages/*`, `@fixtures/*`, `@config/*`, `@testdata/*`, `@utils/*`.

### Re-running the agents

| Agent | Use it to |
|---|---|
| `playwright-test-planner` | Explore the live app and produce a plan under `specs/` |
| `playwright-test-generator` | Turn a plan into specs, running each step in a browser first |
| `playwright-test-healer` | Investigate a failure against the live page and fix it |

---

## What not to "clean up"

| Looks like | Actually |
|---|---|
| A redundant storage reset in `test-base.ts` | `tta-cart-checkout-info` pre-fills checkout and survives a completed order. Measured: the negatives *do* still pass without it today, because each test gets a fresh context — but it is the only guard left the moment anyone adds `storageState` to reuse a login. See `plan.md` |
| A whole spec file of tests asserting broken behaviour | `checkout-known-bugs.spec.ts` **pins** 6 suspected bugs. Passing is not approval; if the app is fixed those tests are *supposed* to fail |
| `toHaveCount(0)` where an invisibility check would read better | The cart badge is removed from the DOM when empty, not hidden |
| `data-test` selectors where `getByRole('button')` would be idiomatic | Checkout, Cancel and Continue Shopping are anchors. The role locator does not find them |
| Two pairs of login tests asserting different things | Empty fields are stopped by native browser validation; whitespace passes it and reaches the app's own banners. Two layers, two assertions |
| A long `assertFunctionNames` list in `eslint.config.mjs` | The rule compares identifiers with `===`, so a glob matches nothing. Listing them also means a new helper is not silently trusted as an assertion |

Never weaken an assertion or delete a scenario to make the suite pass.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| `Playwright Test did not expect test() to be called here` / `two different versions of @playwright/test` | The MCP server started from the wrong directory — resolving `@playwright/test` from the npx cache while the specs resolve it from this folder's `node_modules`. A **dual-copy** problem, not a version mismatch; `-c` pointing at the config does **not** fix it. Open this folder as the workspace root and restart |
| `browser_get_config` or `browser_localstorage_*` returns "not found" | Advertised but not implemented on this server build. Use `page.evaluate`, as the `cleanSession` fixture does |
| Login fails against a username you never configured | The `USERNAME` collision. Your key must be `TTA_USERNAME` |
| `Missing required environment variable TTA_PASSWORD` | Working as intended — `@config/env` fails loudly rather than logging in with a blank password |
| Blank-field negatives pass when they should fail | Storage was not cleared, so the form was pre-filled. Check `cleanSession` is intact |
| A price or product-name assertion fails | Assertions copied from a saucedemo suite will not work here. The first alphabetical item is the red T-shirt at `$15.99`, not `Sauce Labs Backpack` |
| `Test has no assertions` from ESLint on a test that clearly asserts | Its assertion goes through a page-object helper. Add the helper's name to `assertFunctionNames` in `eslint.config.mjs` |
| `git push` dies with `OpenSSL SSL_connect: Connection was reset` | This remote resets the first attempt or two. Retry until local `HEAD` matches `origin` |
