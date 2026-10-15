# Sample results

Two runs of the same 100-test end-to-end suite for a fictional shop, in Playwright's JSON report format. They are
the sample input of the [Flaky Test Case Finder](../README.md#the-sample-data).

| File | Run | Tests | Passed | Failed | Passed on retry |
|---|---|---|---|---|---|
| [result1.json](result1.json) | First | 100 | 97 | 3 | – |
| [result2.json](result2.json) | Second | 100 | 97 | 2 | 1 |

Comparing them should find exactly two flaky tests. To use your own suite, point the flow at any folder holding
two reports named exactly `result1.json` and `result2.json`:

```bash
npx playwright test --reporter=json > result1.json
npx playwright test --reporter=json > result2.json
```
