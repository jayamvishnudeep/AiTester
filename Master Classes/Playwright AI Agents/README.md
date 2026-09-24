# Playwright AI Agents — TTACart End-to-End Suite

Three Playwright agents — a planner, a generator and a healer — driving a real
browser through [TTACart](https://app.thetestingacademy.com/playwright/ttacart/),
a storefront demo. The planner explored the live app and wrote the test plan;
the generator executed every step in the browser and wrote the specs; the healer
repairs them when they break.

| | |
|---|---|
| **Application under test** | `https://app.thetestingacademy.com/playwright/ttacart/` |
| **Plan** | 24 scenarios, written from live exploration |
| **Suite** | 25 tests (24 scenarios + seed), green in ~45s |
| **Built with** | Playwright 1.63, the `playwright-test` MCP server |
| **Agents** | `playwright-test-planner`, `-generator`, `-healer` |

---

## Contents

| File | What it is |
|---|---|
| `specs/ttacart-e2e-order-plan.md` | The test plan. 613 lines, 24 scenarios — the authoritative document |
| `src/ttacart-e2e-order.spec.ts` | All 24 scenarios, in three describes mirroring the plan |
| `src/seed.spec.ts` | The generator's seed file — leave it alone |
| `playwright.config.ts` | `testDir: ./src`, chromium, `dotenv.config()` |
| `.mcp.json` | The `playwright-test` MCP server, for Claude Code |
| `.vscode/mcp.json` | The same server, for VS Code |
| `.github/agents/` | The three agent definitions |
| `plan.md` | Why it is built this way |

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
| A stray `localStorage.clear()` in `beforeEach` | `tta-cart-checkout-info` pre-fills checkout and survives a completed order. Without the clear, every blank-field negative passes on stale values |
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
