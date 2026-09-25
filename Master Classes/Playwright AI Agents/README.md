# Playwright AI Agents — TTACart End-to-End Suite

Three Playwright agents — a planner, a generator and a healer — driving a real
browser through [TTACart](https://app.thetestingacademy.com/playwright/ttacart/),
a storefront demo. The planner explored the live app and wrote the test plan;
the generator executed every step in the browser and wrote the specs; the healer
repairs them when they break.

| | |
|---|---|
| **Application under test** | `https://app.thetestingacademy.com/playwright/ttacart/` |
| **Plan** | 24 scenarios, plus a 9-scenario addendum, all written from live exploration |
| **Suite** | 34 tests (33 scenarios + seed), green in ~1.8m headed |
| **Suspected bugs pinned** | 6 — two in the primary plan, four found by the addendum |
| **Built with** | Playwright 1.63, the `playwright-test` MCP server |
| **Agents** | `playwright-test-planner`, `-generator`, `-healer` |

---

## Contents

| Path | What it is |
|---|---|
| `specs/ttacart-e2e-order-plan.md` | The test plan. 613 lines, 24 scenarios — the authoritative document |
| `specs/ttacart-extended-negative-plan.md` | Addendum: 9 more scenarios, and the four bugs they found |
| `src/specs/` | The four spec files, mirroring the plans' sections |
| `src/pages/` | One class per page, plus `BasePage` for the shared header shell |
| `src/flows/OrderFlow.ts` | Multi-page preconditions ("logged in, one item, on checkout") |
| `src/fixtures/tta-test.ts` | The `test`/`expect` specs import, wiring the page objects and the storage reset |
| `src/fixtures/test-data.ts` | Every verified URL, price, string and error message |
| `src/seed.spec.ts` | The generator's seed file — leave it alone |
| `playwright.config.ts` | `testDir: ./src`, chromium, `dotenv.config()` |
| `.mcp.json` | The `playwright-test` MCP server, for Claude Code |
| `.vscode/mcp.json` | The same server, for VS Code |
| `.github/agents/` | The three agent definitions |
| `plan.md` | Why it is built this way |

### How the suite is put together

Specs import `test` and `expect` from `src/fixtures/tta-test.ts`, never from
`@playwright/test` directly — that import is what supplies the page objects and
the storage reset. A test names the pages it needs as fixtures:

```ts
test('Last Name left blank is rejected', async ({ orderFlow, checkoutInformationPage }) => {
  await orderFlow.reachCheckoutStepOne();
  await checkoutInformationPage.fillDetails('John', '', '12345');
  await checkoutInformationPage.continue();
  await checkoutInformationPage.expectError(ERRORS.lastNameRequired);
});
```

Page objects hold locators and actions, plus `expect*` helpers limited to page
*identity* and *shell state* (`expectLoaded`, `expectCartBadgeAbsent`).
Everything scenario-specific stays in the spec, where a reader can see what the
test actually claims.

The plan is worth reading before the specs. Every selector, price and error
string in it was read off the running application, and §5–§6 record what the
exploration found that the scenarios alone do not say — how the other five
usernames behave, and two suspected application bugs.

---

## Requirements

- **Node.js 20+** (developed on v24)
- **A `.env` file** in this folder — see setup
- The `playwright-test` **MCP server**, only if you want to re-run the agents.
  The committed suite runs without it.

---

## Setup

**1. Install dependencies and the browser.**

```bash
npm install
npx playwright install chromium
```

**2. Create `.env` in this folder.**

```ini
BASE_URL=https://app.thetestingacademy.com/playwright/ttacart/
TTA_USERNAME=standard_user
TTA_PASSWORD=<the demo password>
```

The `TTA_` prefix is not decoration. Windows defines `USERNAME` as a system
environment variable, and `dotenv` will not overwrite a variable that is already
set — a bare `USERNAME=` key is silently ignored and your Windows account name
is sent to the login form instead. `.env` is gitignored; never hardcode the
credentials into a spec.

**3. Open *this folder* as the workspace root** if you intend to use the agents.
Not the repository root. The MCP server inherits its working directory from the
editor, and starting it anywhere else breaks it — see troubleshooting.

---

## Usage

Run the suite headed, which is how this project runs it:

```bash
npx playwright test --headed --reporter=list
```

```
25 passed (45s)
```

| Command | What it does |
|---|---|
| `npx playwright test --headed --reporter=list` | The whole suite, visible |
| `npx playwright test --headed src/specs/ttacart-login-negative.spec.ts` | One section |
| `npx playwright test --headed -g "happy path"` | One scenario by name |
| `npx playwright test --ui` | Pick and step through tests interactively |
| `npx playwright show-report` | The HTML report from the last run |

### Re-running the agents

Do not write or repair specs by hand — that is what the three agents are for.

| Agent | Use it to |
|---|---|
| `playwright-test-planner` | Explore the live app and produce a plan under `specs/` |
| `playwright-test-generator` | Turn a plan into specs, running each step in a browser first |
| `playwright-test-healer` | Investigate a failure against the live page and fix it |

---

## What not to "clean up"

Four things in the suite look like tidying opportunities and are load-bearing.
Each is explained where it appears; the short version:

| Looks like | Actually |
|---|---|
| A redundant storage reset in `tta-test.ts` | `tta-cart-checkout-info` pre-fills checkout and survives a completed order. Measured: the negatives *do* still pass without it today, because each test gets a fresh context — but it is the only guard left the moment anyone adds `storageState` to reuse a login. See `plan.md` |
| Two tests asserting broken behaviour | §4.7 and §4.8 **pin suspected bugs**. Passing is not approval, and both say so |
| `toHaveCount(0)` where a visibility check would read better | The cart badge is removed from the DOM when empty, not hidden |
| `data-test` selectors where `getByRole('button')` would be idiomatic | Checkout, Cancel and Continue Shopping are anchors. The role locator does not find them |
| §3.4/3.5 and §3.6/3.7 asserting different things about the same form | Empty fields are stopped by native browser validation; whitespace passes it and reaches the app's own banners. Two layers, two assertions |

Never weaken an assertion or delete a scenario to make the suite pass.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| `Playwright Test did not expect test() to be called here` / `two different versions of @playwright/test` | The MCP server started from the wrong directory. It is resolving `@playwright/test` from the npx cache while the specs resolve it from this folder's `node_modules`. It is a **dual-copy** problem, not a version mismatch — `-c` pointing at the config does **not** fix it. Open this folder as the workspace root and restart |
| `browser_get_config` or `browser_localstorage_*` returns "not found" | Advertised but not implemented on this server build. Use `page.evaluate` for storage, as the suite's `beforeEach` does |
| Login fails against a username you never configured | The `USERNAME` collision. Your key must be `TTA_USERNAME` |
| The credentials arrive as empty strings | `.env` is missing, or is not in this folder. `dotenv.config()` runs from `playwright.config.ts` and resolves relative to the process working directory |
| Blank-field negatives (§4.1–4.4) pass when they should fail | Storage was not cleared, so the form was pre-filled. Check the `beforeEach` is still intact |
| A price or product-name assertion fails | Assertions copied from a saucedemo suite will not work here. TTACart's first alphabetical item is the red T-shirt at `$15.99`, not `Sauce Labs Backpack` |
| `git push` dies with `OpenSSL SSL_connect: Connection was reset` | This remote resets the first attempt or two. Retry until local `HEAD` matches `origin` |
