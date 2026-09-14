# Flaky Test Case Finder

A Langflow agent that reads two Playwright runs of the same test suite and tells
you which tests are **flaky** — and, just as importantly, which ones only look
flaky but are actually broken.

![The Langflow Playground showing the finished run. The reply opens with "2 out of 100 tests compared are flaky", then lists the two flaky tests with what each did in run 1 and run 2, then a separate "Not flaky - actually broken" section naming the two tests that failed in both runs, and finally three recommended actions. The run finished in 3.3 seconds using 978 tokens](Flow_Flaky_Test_Finder_result.png)

---

## The problem this solves

A test that fails today and passes tomorrow tells you nothing, and it costs a QA
team real hours. But a failing test is not automatically flaky. Run a suite twice
and you get two lists of failures, and the interesting question is what changed
between them:

| Run 1 | Run 2 | What it means |
|---|---|---|
| failed | passed | **Flaky** — the test disagrees with itself |
| passed | failed | **Flaky** — same thing, other direction |
| failed | failed | **A real defect.** Re-running will not help |
| passed | passed | Healthy |

Playwright also flags a test that failed and then passed **on retry inside one
run**. That is flaky too, and this agent counts it.

Getting this wrong is expensive in both directions: quarantine a genuine defect
and you ship the bug, chase a flaky test as a bug and you waste a morning.

---

## What is in this folder

| File | What it is |
|---|---|
| `Flaky_Test_Finder_langflow_flow.json` | The flow. Import this into Langflow |
| `flaky_comparator.py` | The comparison logic, readable on its own |
| `results/result1.json` | First test run — 100 tests |
| `results/result2.json` | Second test run — the same 100 tests |
| `Flow_Flaky_Test_Finder_result.png` | The screenshot above |

The Python file is the same code that is embedded inside the flow JSON. It is
kept here separately so you can read it without opening Langflow.

---

## The sample data

Two runs of a 100-test end-to-end suite for a fictional shop:

```
result1.json    100 tests    97 passed    3 failed
result2.json    100 tests    97 passed    2 failed    1 passed on retry
```

Four tests are interesting, and the agent should find exactly **two flaky**:

| Test | Run 1 | Run 2 | Verdict |
|---|---|---|---|
| `catalog/search.spec.ts` → type-ahead suggestions | failed | passed | **flaky** |
| `media/upload.spec.ts` → avatar preview | passed | passed on retry | **flaky** |
| `checkout/payment.spec.ts` → expired card error | failed | failed | broken |
| `auth/login.spec.ts` → account lockout | failed | failed | broken |

The two groups even fail differently, which is a useful habit to notice. The
flaky pair fail on **timeouts** — something did not arrive in 5000 ms. The broken
pair fail on **value mismatches** — the lockout triggers after six attempts
instead of five, and the expired-card message reads "Something went wrong."

Both files are genuine Playwright JSON reporter output: nested `describe` suites,
one entry per attempt, stable test ids, ANSI-coloured error text.

---

## Before you start

You need three things:

1. **Langflow running** — normally at `http://127.0.0.1:7860`
2. **A Groq API key** — free from [console.groq.com](https://console.groq.com)
3. **This repo cloned** somewhere you can point at

---

## Setup

### 1. Store your Groq key in Langflow

The flow looks the key up by name, so it is never written into the JSON.

- In Langflow, open **Settings → Global Variables → Add New**
- Name it exactly **`GROQ_API_KEY`**
- Type **Credential**, value = your key

### 2. Import the flow

On the Langflow home screen choose **New Flow → Import**, and pick:

```
Flaky_Test_Finder_langflow_flow.json
```

Five nodes appear on the canvas.

### 3. Point it at your results folder

This is the one value you **must** change after cloning, because it holds an
absolute path from the machine the flow was built on.

- Click the **Flaky Test Comparator** node
- Find **Default results folder**
- Replace it with the full path to this folder's `results` directory

```
C:/Users/you/AiTester/09_LangFlow/03_Flaky_Test_case_Finder/results
```

Forward slashes work fine on Windows. Any folder is acceptable as long as it
contains files named `result1.json` and `result2.json`.

---

## Running it

Open **Playground**, type anything — `run` will do — and press Enter.

The words are ignored. The Chat Input exists so the Playground has somewhere to
send; the comparator checks whether what arrived is a real folder, and when it is
not, it uses the default folder you set in step 3.

You should see the report in about three seconds, opening with:

```
2 out of 100 tests compared are flaky.
```

### Comparing a different pair

Paste a folder path into the chat box instead of `run`:

```
C:/some/other/folder/with/two/reports
```

---

## What comes back

| Section | What it holds |
|---|---|
| **Opening line** | How many tests are flaky, out of how many compared |
| **Flaky tests** | Each one named, what it did in each run, and the likely cause |
| **Not flaky - actually broken** | Failed in both runs, so re-running will not help |
| **What to do next** | Two or three concrete actions |

---

## Using it on your own test suite

Produce two JSON reports from the same suite:

```bash
npx playwright test --reporter=json > result1.json
npx playwright test --reporter=json > result2.json
```

Drop both into a folder, point the node at it, and run. Nothing else changes —
the comparison reads any Playwright JSON report, with or without `describe`
blocks, retries or multiple projects.

For a fair comparison the two runs should cover the same tests. A test that
appears in only one of them is reported separately rather than counted as flaky.

---

## How it works

```
[ Chat Input ] -> [ Flaky Test Comparator ] -> [ Prompt ] -> [ Groq ] -> [ Chat Output ]
   somewhere to      reads both reports,        briefs the    writes      the report
   type into         works out the verdict      model         the prose
```

**The counting is plain Python, not the model.** The comparator walks both suite
trees, matches tests by their Playwright id, compares outcomes and produces exact
counts. The language model receives that finished comparison and only writes it
up. Ask an LLM to diff 200 test results directly and it will miscount without
telling you; here the numbers cannot drift, and the same input always gives the
same answer.

The model is `qwen/qwen3.8-27b` on Groq, capped at 900 output tokens with
temperature 0.1.

### Calling it from code

Useful once you want this in CI rather than in a browser:

```bash
curl -X POST "http://127.0.0.1:7860/api/v1/run/<your-flow-id>?stream=false" \
  -H "Content-Type: application/json" \
  -H "x-api-key: <your-langflow-key>" \
  -d '{
        "output_type": "chat",
        "input_type": "chat",
        "input_value": "run",
        "tweaks": {
          "FlakyTestComparator-Fk9Qa": {
            "results_dir": "/path/to/your/results"
          }
        }
      }'
```

Your flow id is the long value in Langflow's address bar after `/flow/`. The
`tweaks` block overrides the folder for a single request without editing the
saved flow.

---

## If something does not work

| What you see | What to do |
|---|---|
| `no readable results folder` | Step 3 — set **Default results folder** to a real path |
| `Run 1: no file at ...` | The folder needs files named exactly `result1.json` and `result2.json` |
| `is not valid JSON` | That file is not a Playwright JSON report. Check the `--reporter=json` output |
| Playground sends but nothing happens | Reload the browser tab — the canvas caches the old version after an import |
| An error about the API key | The global variable must be named exactly `GROQ_API_KEY` |
| `One of the reports contained no tests` | The file parsed but held no suites — likely an empty or partial run |
| The reply stops mid-sentence | Raise **Max Tokens** on the Groq node above 900 |
