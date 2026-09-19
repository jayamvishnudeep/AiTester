# Regression plan

*Generated 2026-09-19 by the Smart Regression Advisor. The selected set is computed from the repository's import graph — every test below carries the path it was reached by.*

## At a glance

| | |
|---|---|
| Files changed | 1 |
| Source files indexed | 13 |
| Tests in the suite | 5 |
| **Tests selected** | **1 of 5** — 80% skipped |
| Must run | 1 |
| Should run | 0 |

## What changed

| File | Change | Lines |
|---|---|---:|
| `src/utils/money.ts` | modified | 2 |

## Tests to run

| Tier | Test | Reached from | Hops |
|---|---|---|---:|
| must_run | `tests/checkout.spec.ts` | `src/utils/money.ts` | 1 |

## Run it

```bash
# typescript
npx playwright test tests/checkout.spec.ts
```

---

## Advice

*This section is written by a language model from the evidence above. The selected set is not its work; the ordering and the risk assessment are.*

**What changed**
The diff modifies `src/utils/money.ts`, a utility module likely responsible for currency formatting or calculation. The risk is concentrated in data integrity: if the logic for rounding, symbol placement, or decimal precision shifts, any consumer relying on exact string matches or numerical equality will fail. Since this is a leaf utility, the blast radius is limited to direct importers, but the impact on user-facing financial data is high.

**Run these first**
1. `tests/checkout.spec.ts`: This is the sole selected test and the only direct importer of the changed file. It validates the end-to-end flow where money values are rendered or calculated. Running this first provides the fastest signal on whether the core financial logic remains intact. If this passes, the immediate structural risk is mitigated.

**What could still bite**
1. **Values read by name at runtime**: If `money.ts` relies on environment variables for currency symbols or tax rates, the test suite might pass in a default environment but fail in production where those values differ. The import graph cannot see these dynamic dependencies.
2. **Shared state between tests**: If `checkout.spec.ts` or other skipped tests rely on a seeded database state that includes pre-formatted monetary values, a change in formatting logic could cause mismatches during data validation steps that are not directly tied to the import path of `money.ts`.

**The Trade**
The value of skipping 80% of the suite is speed; you get a signal in seconds rather than minutes. However, the cost is significant here. Because `money.ts` is a foundational utility, it is highly likely that other modules (e.g., invoice generation, reporting) import it indirectly or use its output in ways not captured by the single-hop analysis. A skipped test that validates a secondary consumer of this utility cannot fail, meaning a subtle formatting bug could slip through to production. For a financial utility, the cost of a missed regression outweighs the time saved by skipping the broader suite. I recommend running the full suite if time permits, or at least manually verifying one secondary consumer.

---

## What this analysis cannot see

The tests left out are left out on the strength of a static import graph. These couplings are real and invisible to it, and any of them can mean a skipped test would have caught the change:

- A selector or test id matching markup the test never imports. Changing an id in a component breaks the page object that looks for it, with no edge between them - which is the coupling agent 12 in this section exists to repair.
- Anything across an HTTP or process boundary. A test calling an endpoint implemented elsewhere has no import path to it.
- Database migrations, seed data and stored procedures, which reach tests through the data rather than through code.
- Values read by name at runtime - environment variables, feature flags, system properties.
- Cucumber and other BDD glue, which binds steps to features by regular expression rather than by import.
- Shared state between tests: a seeded account, a tenant, a port, a browser profile. A change that makes one test leave dirt behind breaks another that imports nothing from it.
- Timing. A change that makes a page slower can trip a timeout in a test with no structural relationship to it.
