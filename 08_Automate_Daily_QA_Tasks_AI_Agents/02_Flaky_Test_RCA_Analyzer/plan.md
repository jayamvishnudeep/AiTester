# Plan — Flaky Test RCA Analyzer (n8n AI Agent)

An SDET points the agent at a test that keeps flapping. It pulls the logs from
several runs, finds the pattern across them — `Network Timeout`, a stale
locator, a shared-state collision — and comes back with a named cause, the
evidence it read that from, and a concrete fix suggestion.

Status: **built and tested against the live Groq API.** Forty assertions pass,
including two real model calls. Not yet imported into n8n Cloud.

## The brief

| | |
|---|---|
| Audience | SDET |
| Problem | Hard to find *why* a test is flaky |
| Input | Logs from multiple flaky runs |
| Output | Pattern analysis and a fix suggestion |
| Given shape | Webhook → HTTP Request (fetch multi-run logs) → AI Agent (pattern detective) → Structured Output → Slack |

## Why this is not the same job as the screenshot agent

`01_Screenshot_To_Bug_Reporter` reads **one** artefact and describes it. This one
reads **many** and has to find what they share. That difference drives every
design decision below:

- A single run cannot show flakiness. The agent must refuse to call a pattern
  from one failure the way the screenshot agent refuses to invent repro steps.
- Multi-run logs are *large*, and the token budget is the hard constraint here
  rather than the model's ability.
- The interesting output is not a description, it is a **frequency claim** —
  "seven of nine failures ended in the same socket timeout" — which means the
  evidence has to be counted, not summarised.

## Model and the constraint that shapes the build

Checked against the live Groq account rather than the docs.

`GET /openai/v1/models` returns **14 models**. Discounting the audio (`whisper`),
guard (`llama-prompt-guard`) and Arabic/English speech models, the real
candidates are:

| Model | Note |
|---|---|
| `openai/gpt-oss-120b` | Largest. Best at holding several logs at once |
| `openai/gpt-oss-20b` | Faster, weaker on cross-run correlation |
| `qwen/qwen3.6-27b` | Thinking model — needs `reasoning_effort: none` or it eats the budget |

**Going with `openai/gpt-oss-120b`.** Correlating failure signatures across runs
is the whole task, and it is the strongest model available for it. Cost is $0 on
the free tier.

### The limit that actually bites

Measured from the live response headers on both gpt-oss models:

```
x-ratelimit-limit-requests: 1000     per day
x-ratelimit-limit-tokens:   8000     per minute
```

**8,000 tokens per minute is the binding constraint, and it is an *input*
limit.** Yesterday's agent was constrained on output; this one is constrained on
how much log it can show the model at all. Roughly:

```
8,000 tokens  ~=  32,000 characters total per minute
  - instructions and schema     ~1,300 tokens
  - reserved for the answer     ~1,000 tokens
  = ~5,700 tokens of log        ~=  22,000 characters
```

Across nine runs that is about **2,400 characters per run** — perhaps 30 lines.
A single Playwright or Selenium failure log is far bigger than that.

So the agent cannot simply forward the logs. Deciding *which 30 lines matter* is
the core engineering problem, and it belongs in code, not in the prompt.

## The pipeline

```
Webhook Trigger        POST /flaky-rca  {test_name, runs_url | runs[]}
  -> Fetch Run Logs    (HTTP Request)  pull the multi-run history
  -> Budget The Evidence (Code)        normalize, extract failure regions, fit the budget
  -> Flaky Pattern Detective (AI Agent + Groq + Structured Output Parser)
  -> Validate Analysis (Code)          schema check and defaults before anything leaves
  -> Post to Slack     (Slack)         the analysis as a readable message
  -> Respond to Webhook                same JSON back to whoever called it
```

Seven nodes. The given shape is five; the two additions are the Code nodes, and
both exist for reasons the brief implies rather than states.

Node type versions taken from workflows already in this repo, so they match the
n8n version actually in use: `webhook` v2, `httpRequest` v4.5, `code` v2,
`agent` v3.1, `lmChatGroq` v1, `outputParserStructured` v1.3, `slack` v2.3,
`respondToWebhook` v1.

### Webhook Trigger

`POST /flaky-rca`, `responseMode: responseNode` so the caller gets the analysis
back rather than an immediate empty 200. Body:

```json
{
  "test_name": "checkout.spec.ts > applies percentage discount",
  "runs_url": "https://ci.example.com/api/tests/checkout-discount/runs?limit=10",
  "runs": []
}
```

`runs` is an escape hatch: post the logs inline and the HTTP fetch is skipped.
That is what makes the workflow testable without a CI system attached, and it is
how I intend to prove it works.

### Fetch Run Logs (HTTP Request)

GET against `runs_url`, `neverError: true` so a 404 from the CI becomes a
handled state rather than a dead execution. Whatever it returns is normalised in
the next node — the agent should not care whose CI it is.

### Budget The Evidence (Code) — the important one

Four jobs:

1. **Normalise.** Accept an array of runs, `{runs: [...]}`, `{items: [...]}` or
   a single run, and reduce each to `{run_id, status, started_at, duration_ms,
   log}`. Different CI systems, one internal shape.
2. **Extract the failure region.** Not the last N lines blindly — scan for the
   lines that carry signal (`Error`, `Timeout`, `ECONNRESET`, `StaleElement`,
   `AssertionError`, `Expected`/`Received`, stack frames) and take a window
   around them. A 4,000-line log usually has 20 useful lines.
3. **Fit the budget.** Estimate at 4 characters per token, cap the whole
   evidence block at ~22,000 characters, and divide it evenly across runs so one
   noisy run cannot crowd out the other eight. Record what was dropped.
4. **Count before the model sees anything.** Runs, passes, failures, flakiness
   rate and a naive signature tally are computed **in code**. The model is asked
   to explain the pattern, not to do arithmetic — models are unreliable at
   counting and this is a frequency claim.

It also emits `truncated: true/false` and `evidence_completeness`, which the
prompt requires the model to take into account when setting confidence.

### Flaky Pattern Detective (AI Agent + Structured Output Parser)

An Agent node with `lmChatGroq` and `outputParserStructured` attached, which is
the shape the brief asks for and a deliberate contrast with
`01_Screenshot_To_Bug_Reporter`, where JSON mode was unavailable and parsing had
to be hand-rolled. Both approaches now exist in the repo to compare.

The system message carries the contract: the taxonomy, the evidence rules, and
the refusals.

### Validate Analysis (Code)

The output parser is not trusted as the last line of defence. This node checks
every field against the schema, defaults anything missing, clamps the enums, and
verifies that each quoted piece of evidence **actually appears in the log text
that was sent**. A fabricated quotation is the one failure that would make the
whole tool untrustworthy, and it is cheap to detect.

### Post to Slack, and Respond to Webhook

A readable message — pattern, flakiness rate, category, the evidence lines, the
fix suggestion, and the recommendation. The same JSON is returned to the caller
so the agent is usable from a script as well as from Slack.

## What the model is asked to produce

```
test_name
runs_analyzed            counted in code, echoed
failed_runs / passed_runs
flakiness_rate           counted in code
dominant_pattern         "Network Timeout", or "No Dominant Pattern"
pattern_frequency        how many failing runs show it
category                 one of the taxonomy below
evidence                 [{run_id, quoted_line}]  verbatim, never paraphrased
failure_signatures       [{signature, occurrences}]
suspected_cause          why this pattern produces intermittency
fix_suggestion           concrete and actionable
fix_type                 Test Fix | Product Fix | Infrastructure Fix | Unable to Determine
recommendation           Fix Now | Quarantine | Monitor | Not Flaky
confidence               High | Medium | Low
missing_information      what to collect to raise confidence
```

### Category taxonomy

Written for flakiness specifically, in the style of the severity and category
vocabularies in `07_.../02_BugTriage` so the outputs read consistently:

```
Timing and Race Condition      fixed sleeps, unawaited async, animation
Network or Timeout             socket timeouts, connection resets, slow upstream
Test Data and State            leftover records, non-unique fixtures
Environment and Infrastructure runner load, container start, clock skew
Selector or Locator            stale element, changed DOM, index-based lookup
Test Ordering and Shared State passes alone, fails in the suite
Resource Exhaustion            memory, file handles, connection pools
External Dependency            third-party sandbox, rate limit
Assertion Tolerance            exact match on something inherently variable
Unable to Determine
```

## The guard rails

Three, and they are the reason to trust the output.

**1. One failure is not a pattern.** With fewer than two failing runs the agent
must return `dominant_pattern: "Insufficient Runs"`, confidence `Low`, and ask
for more history. This is the direct analogue of the screenshot agent refusing
to invent reproduction steps, and it is the failure mode a flakiness tool is
most prone to — a single stack trace looks like an explanation.

**2. Evidence must be quoted, never paraphrased.** Every claim carries a
`run_id` and a verbatim line. The validation node checks the quote really occurs
in the log that was sent. A plausible-sounding cause with no line behind it is
worse than "Unable to Determine", because an SDET will act on it.

**3. Failures that do not cluster are not one bug.** If the runs fail for
different reasons the honest answer is `No Dominant Pattern` plus the separate
signatures, not the most impressive-sounding of them. A test can be genuinely
broken in three ways.

Plus the standing rule from `01_LLM_Basics`: anything undeterminable is
`Unable to Determine`, and the logs are the only permitted source.

## What was found by building it

Four things only showed up against the live API and the real node source, and
all four changed the workflow.

**The n8n Groq node cannot turn reasoning down.** Read from
`packages/@n8n/nodes-langchain/nodes/llms/LmChatGroq/LmChatGroq.node.ts`, it
exposes exactly three settings: model, `maxTokensToSample` and temperature.
There is no `reasoning_effort`.

**That matters because gpt-oss reasons before it answers, and the reasoning is
billed as completion.** The first live call, with a 900-token ceiling, came back
as `400 json_validate_failed` with an **empty** `failed_generation` — the model
had spent the entire allowance thinking and emitted nothing. This is yesterday's
qwen lesson in a new costume, except the lever that fixed it there is not
available here. The only remaining lever is room, so `maxTokensToSample` is set
to **3000**.

Worth noting for later: `reasoning_effort: 'none'` is rejected by gpt-oss —
`must be one of low, medium, or high`. qwen accepts `none`. They are not
interchangeable.

**Giving the answer room forced the evidence budget down.** The original plan
allowed 22,000 characters of log. With ~1,100 tokens of system message, ~400 of
injected schema and ~3,000 reserved for the answer, that no longer fits inside
8,000. The budget is now **12,000 characters**, and the measured call sits at
prompt 2,492 + completion 1,432 = **3,924 tokens**, comfortably inside.

**The first signal line is the wrong thing to key a signature on.** Taking the
first interesting line meant runs that died on the identical timeout were keyed
on whatever noise came earliest — a `DEBUG payments-client retrying request`
line — so five identical failures split into buckets of three and two and *no
pattern clustered at all*. Ranking candidate lines by severity first
(`Error:`, `Timeout … exceeded`, `ECONNRESET`, `AssertionError`) collapsed them
correctly to 5. Without this the agent's central job silently fails.

A smaller one: the per-run budget covers log text only, so run headers pushed
the assembled block 106 characters over the cap. The block is now trimmed as a
final step, because the ceiling has to hold for the whole thing, not its parts.

## Test result

Both Code nodes are executed with mocked n8n globals, and two real Groq calls
are made with the real system message — so what is tested is what ships.
**Forty assertions, all passing.**

Against `sample_runs.json` (nine runs, six failing: five sharing a socket
timeout, one failing on an unrelated rounding assertion):

```
tokens: prompt 2492, completion 1432, total 3924   |  3.5s
pattern:  Network Timeout  (5 of 6 failures)
category: Network or Timeout      confidence: High      fix_type: Test Fix
cause:    the payments-sandbox resets the TCP connection or hits a rate limit,
          so page.waitForResponse never resolves
fix:      stub the payments sandbox, or add exponential backoff and raise the
          waitForResponse timeout
```

The three things worth noting in that output:

- It found the pattern at **exactly 5 of 6** — the arithmetic the code handed it.
- **It did not take the bait.** The rounding assertion in run 8871 is a real
  failure and a plausible-sounding cause, and it was correctly left out of the
  dominant pattern.
- **All ten quoted lines survived verification** against the logs actually sent.

The guard rail was tested live too: given a single failing run, the model itself
returned `Insufficient Runs` at Low confidence, and the validator enforced the
same result independently.

The budgeting node was also checked against a 90,000-character log of pure
noise with one error buried in it — it extracted 234 characters containing the
error — and against a log that is nothing but error lines, where it clipped to
the budget and marked the evidence `Partial`.

The validator was checked by feeding it a **fabricated quotation**
(`Error: the database exploded`). It dropped the quote, recorded why in
`validation_notes`, and lowered confidence to Low.

## Deliverables

```
02_Flaky_Test_RCA_Analyzer/
├── plan.md                                  this file
├── Flaky_Test_RCA_Analyzer_n8n_workflow.json
├── sample_runs.json                          synthetic history for testing
└── README.md                                 written after it is proven
```

## Decisions taken

Both open questions were answered before building.

**1. Log source — a generic endpoint, plus inline runs.** The HTTP Request node
GETs a `runs_url` supplied per call, so the agent works against any CI rather
than being welded to one. The webhook also accepts a `runs[]` array inline,
which skips the fetch entirely — that is the escape hatch that makes the
workflow testable today with no CI attached, and it is how the live test below
was run.

**2. Output — Slack, with a Telegram fallback.** Slack is the primary node, as
the brief specifies. A Telegram node is wired in parallel and shipped
**disabled**, so it costs nothing until enabled; this repo already has a working
Telegram credential while Slack needs one adding.

The Slack node is set to `onError: continueRegularOutput` for the same reason
the screenshot agent lets its Jira attachment fail softly: a missing Slack
credential should not swallow the analysis. The webhook still responds with the
full JSON, and Telegram still fires if enabled.

## Deliberately not in v1

- **No writing back to the test suite.** The agent recommends a fix; it does not
  open a PR. A wrong automated fix to a flaky test is how a flaky test becomes a
  silently skipped one.
- **No quarantine automation.** `recommendation: Quarantine` is advice for a
  human, not an action.
- **No historical trend storage.** Each run analyses the window it is given. A
  Sheets or database sink would be the natural v2, and would let the agent say
  "this started three weeks ago".
- **No multi-test batch mode.** One test per call, because the token budget is
  already the constraint.
