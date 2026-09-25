# Plan — Playwright AI Agents (TTACart end-to-end suite)

| | |
|---|---|
| **Role** | SDET |
| **Problem** | A generated suite is only worth as much as the exploration behind it |
| **Input** | A live application and nothing else — no documentation, no existing tests |
| **Output** | A verified test plan, and 24 scenarios automated from it |
| **Shape** | planner → plan → generator → specs → healer → green |
| **Structure** | Page objects, composable state fixtures, area-organised specs |

## Why the structure follows AdvancePlaywrightFramework2x

The layout here is deliberately the one from
[AdvancePlaywrightFramework2x](https://github.com/PramodDutta/AdvancePlaywrightFramework2x):
`src/` split into `pages/`, `fixtures/`, `config/`, `testdata/`, `utils/` and
`tests/`, path aliases, `BasePage` supplying `el` and `log`, locators as
`private readonly`, and specs grouped by area.

Adopting someone else's conventions rather than inventing house ones is the point:
a reader who knows that framework can navigate this repository without being told
anything, and the arguments behind each convention have already been had.

What was **not** adopted is as deliberate. That framework carries an API-testing
progression, an LLM agent layer, five provider transports, a custom reporter and
Ajv schema validation. None of it is here, because none of it has a job here —
this is a UI suite against one application with no API surface under test. Copying
the folders without the need would be the exact thing that framework's own
over-engineering quality gate exists to catch. The one substitution: `logger.ts`
keeps the scope-tagging interface but is dependency-free rather than Winston-backed,
because a transport layer for a 34-test suite that only writes to a console is
weight without a reader.

## Why the suite is a page object model

The 24 scenarios were first written flat: one file, every locator inline, shared
helpers at the top. That is the right shape for the generator agent, which
verifies each step in a browser and writes what it saw, and it is the wrong
shape to keep.

The reason is concentrated in this application's oddities. `[data-test="cancel"]`
being an anchor rather than a button is a fact about TTACart that eight tests
depend on. The cart badge leaving the DOM is a fact that six tests assert
against. Inline, each of those facts is restated at every use, and a change to
the application means finding all of them. In `CartPage` and `BasePage` each is
stated once, next to the comment explaining why it is written that way — so the
explanation travels with the locator instead of being repeated or, worse, lost.

Three rules keep it from becoming the usual page-object mess:

- **Page objects hold locators and actions, not scenarios.** The `expect*`
  methods are limited to page identity and shell state — `expectLoaded`,
  `expectCartBadgeAbsent`. Everything a specific test claims stays in the spec,
  because a test whose assertions are hidden behind method names cannot be read.
- **Multi-page journeys are composable fixtures, not page methods.** "Log in, add
  an item, land on checkout" belongs to none of `LoginPage`, `InventoryPage` or
  `CartPage`, and putting it on any one of them is how a page class turns into a
  god object holding every route through the app. An earlier version kept them in
  an `OrderFlow` class; fixtures are better for a reason that is not cosmetic — a
  fixture is requested by name in the test signature, so the precondition is
  visible in the test's own declaration instead of buried in its first line. They
  chain (`loggedIn` → `cartWithItem` → `atCheckoutInformation` →
  `atCheckoutOverview`), so asking for the deepest runs the stack beneath it.
- **Verified values live in one file.** `test-data.ts` holds the prices, totals
  and verbatim error strings, so the things most likely to change when the app
  changes are in the place you would look first.

## The thing that makes this different from generating tests

The usual failure of an AI-written test suite is not that it is wrong. It is
that it is *plausible*. A model asked to write Playwright tests for a storefront
will produce `Sauce Labs Backpack` at `$29.99`, a `getByRole('button', { name:
'Checkout' })` locator, and an assertion that the cart badge is hidden when
empty. All three are correct for saucedemo.com. All three are wrong here, and
none of them look wrong.

So the rule for both agents is that **nothing is asserted that was not
observed**. The planner did not reason about TTACart, it drove it: every
selector, price, tax figure and error string in the plan was read off the
running page in Chromium. The generator did not write a spec and then run it, it
ran each step first and wrote the assertion from what came back. The plan calls
out each point where TTACart diverges from the application it is modelled on,
because those divergences are exactly where a confidently-generated suite goes
quietly wrong.

That is why the plan is 613 lines for 24 scenarios. Most of it is §1 — the
reference data — and §1 is the part that makes the other sections trustworthy.

## The first item is not the obvious item

Under the default Name (A to Z) sort the first card is `Test.allTheThings()
T-Shirt (Red)` at `$15.99`, ahead of the five `TTA …` products because the
locale comparison puts `Te` before `TT`. It is a small thing, and it is the kind
of small thing that decides whether a suite is real. A model writing from
intuition picks the first product it can name. The value is only knowable by
looking.

For that one item the overview shows `$15.99` + `$1.28` tax = `$17.27`. The 8%
rate was derived from the observed numbers, not assumed from them.

## Two tests that assert broken behaviour on purpose

The exploration turned up two things that look like defects:

- **An empty cart checks out to a completed $0.00 order.** With `Your cart is
  empty.` on screen, Checkout still opens step one, valid details still advance,
  the overview shows `$0.00` with no line items, and Finish produces the full
  `Thank you for your order!` confirmation.
- **The postal code has no format validation at all.** `not-a-zip!!` is accepted,
  persisted, and the order completes. Only emptiness is checked — no length, no
  character class, no numeric constraint.

There were three options. Assert the behaviour a storefront *should* have, and
ship a suite that is red on day one for reasons unrelated to any change anyone
makes. Leave both untested, and lose the record that anyone ever looked. Or pin
the current behaviour and say plainly that it is pinned.

The third is the only honest one, but it carries a real hazard: a green test is
normally a claim that something is *right*, and here it is a claim that
something is *known*. So §4.7 and §4.8 carry comments saying that passing is not
approval, and §6 of the plan records them as suspected bugs rather than baking
them silently into an assertion. **If the application is ever fixed, those two
tests are supposed to fail** — and the comment is what tells the next person
that failing is the good outcome.

## The storage reset, and what measuring it actually showed

TTACart writes the checkout details to `localStorage` under
`tta-cart-checkout-info` on a successful Continue, step one **pre-fills** from
that key on every later visit, and the key is **not** cleared when an order
completes. After a finished order the stored value was still
`{"firstName":"John","lastName":"Doe","postal":"12345"}`.

The consequence would be the nastiest class of test failure — the one with no
symptom. The blank-field negatives in §4.1–4.4 each clear a field and expect
`Error: First Name is required`. Reach step one with that key already set and
the form is not blank when the test arrives, the validation the test exists to
exercise never fires, and the test passes. Four scenarios reporting green while
testing nothing at all, with no error anywhere to notice.

That is the reasoning this suite inherited, and it is worth writing down that
**it was measured rather than believed.** Disabling the reset and running the
eight checkout negatives: all eight still pass. Playwright gives every test its
own browser context, so `localStorage` starts empty regardless. Under the
current configuration the reset is not what is holding those four tests up.

It stays anyway, and the distinction matters more after a page-object refactor
than before it. The obvious next optimisation for a suite where all 24 scenarios
log in is `storageState` — save the session once, reuse it, stop paying for the
login. The moment anyone does that, storage stops being per-test and this
fixture becomes the only thing between §4.1–4.4 and a silent false pass. Serial
mode sharing a context does the same. So the reset is insurance against a change
that a reasonable person is likely to make, and the fixture comment says exactly
that rather than overstating its current role.

Calling it load-bearing when it is not would have been the worse error: the next
person finds the claim, disables it, sees everything still green, and reasonably
concludes the rest of the file's warnings are also inflated.

It is also a deliberate exception to the project's rule that assertions use
web-first `expect(locator)` calls. `page.evaluate` appears exactly once, for
fixture teardown of browser storage, because Playwright exposes no API for it —
and the MCP server's `browser_localstorage_*` tools advertise but resolve as
"not found" on this build.

## Where the DOM disagrees with the idiom

Two more findings that shape the specs.

The cart badge is **removed from the DOM** when the cart is empty, not hidden.
The idiomatic assertion — that the badge is not visible — passes for the wrong
reason on a missing element, and an assertion written as "badge text is empty"
fails outright. The suite uses `toHaveCount(0)`.

Checkout, Cancel and Continue Shopping are **anchors**. Only Login, Continue and
Finish are real buttons. `getByRole('button')` is the better-looking locator and
it simply does not find three of the six controls the flow depends on, so those
use `data-test` attributes — which the application sets consistently across all
six pages, and which are the most stable thing it offers.

## Two kinds of empty are two different tests

§3.4/3.5 (empty username, empty password) assert `validity.valueMissing`.
§3.6/3.7 (whitespace-only) assert the application's error banners. Read side by
side these look inconsistent, and they are testing two different layers.

The fields are `required`, so the browser blocks submission of a genuinely empty
field before the application ever runs — there is no banner to assert, because
no request happened. A space character satisfies `required`, so whitespace
passes native validation, reaches the app, and produces
`Epic sadface: Username is required`. Asserting a banner for the empty case
would be asserting something that cannot exist; asserting `valueMissing` for the
whitespace case would be asserting something the browser never sets.

## The MCP working-directory trap

The `playwright-test` MCP server must run with **this folder** as its working
directory. Started from the repository root it resolves `@playwright/test` out
of the npx cache while the specs resolve it out of this folder's
`node_modules`, and every call fails with:

> You have two different versions of @playwright/test.

The message names the symptom and misdirects the fix. It is a **dual-copy**
problem, not a version-number problem — the same version loaded twice from two
paths is enough to trigger it. Two things were tried and ruled out:

- Passing `-c` to point the server at this folder's `playwright.config.ts`.
  Tested; does not fix it. The config controls test discovery, not module
  resolution.
- Treating it as a version mismatch and reconciling the numbers. There is
  nothing to reconcile; they already match.

The only fix is to start the server in this directory, which in practice means
opening this folder as the workspace root rather than the repository root. Both
`.mcp.json` and `.vscode/mcp.json` therefore live here rather than at the
repository root, and both are deliberately argument-free — the working directory
is doing all the work, and adding flags to the command invites the belief that a
flag could substitute for it.

## Credentials, and one Windows-specific trap

The credentials live in `.env` as `TTA_USERNAME` / `TTA_PASSWORD`, read through
`process.env` and never written into a spec. The prefix is not tidiness.

Windows defines `USERNAME` as a system environment variable, and `dotenv` will
not overwrite a variable that is already set. A `.env` containing `USERNAME=` is
therefore read, ignored, and the Windows account name is submitted to the login
form instead — with no warning from `dotenv`, which considers declining to
overwrite the correct behaviour. The failure surfaces as an authentication error
against a username nobody configured, which sends you looking at the
application rather than at the loader.

## What this suite does not cover

Worth stating, since a green 25 is easy to over-read:

- **One browser.** Chromium only. Nothing here says the flow works in WebKit or
  Firefox.
- **One user.** `standard_user` for the whole positive flow. §5 of the plan
  records why the others are unsuitable: `performance_glitch_user` only delays
  login by four seconds, `visual_user` is functionally identical apart from an
  8px transform on the cart link — a visual-regression fixture, not a functional
  failure case — and only `locked_out_user` earns a scenario of its own.
- **No visual assertions.** The 8px transform above is precisely the sort of
  thing this suite cannot see.
- **A live third-party application.** Every run depends on a deployed demo app
  that can change or disappear without notice. A price change breaks §2.6, and
  that break is legitimate — the assertion was right when it was written.
