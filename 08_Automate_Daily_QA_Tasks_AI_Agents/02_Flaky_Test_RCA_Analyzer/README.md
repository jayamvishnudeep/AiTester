# Flaky Test RCA Analyzer — n8n AI Agent

An SDET points this at a test that keeps flapping. It reads the logs from
several runs, finds what the failures have in common — `Network Timeout`, a
stale locator, a shared-state collision — and comes back with a named cause, the
lines it read that from, and a concrete fix.

Exported as `Flaky_Test_RCA_Analyzer_n8n_workflow.json`. The build log, with the
model research and everything that only showed up against the live API, is in
[`plan.md`](plan.md).

## Why this is harder than it looks

The sibling agent in [`01_Screenshot_To_Bug_Reporter`](../01_Screenshot_To_Bug_Reporter_AI_Agent)
reads **one** artefact and describes it. This one reads **many** and has to find
what they share, which changes everything:

- A single run cannot show flakiness. One failing run is a stack trace, not a
  pattern — and a stack trace always *looks* like an explanation.
- The output is a **frequency claim** ("five of six failures ended in the same
  socket timeout"), so the evidence has to be counted, not summarised.
- Multi-run logs are enormous, and the token budget — not the model — is the
  binding constraint.

## The constraint that shapes the whole design

Measured from Groq's live response headers:

```
x-ratelimit-limit-requests: 1000     per day
x-ratelimit-limit-tokens:   8000     per minute
```

**8,000 tokens per minute, and it is an *input* limit.** After the system
message (~1,100 tokens), the schema the output parser injects (~400) and the
room the answer needs (~3,000), about **12,000 characters of log** are left for
all runs combined. A single Playwright failure log is bigger than that.

So the agent cannot forward the logs. Deciding *which lines matter* is the real
work, and it belongs in code.

## The pipeline

```
Webhook          POST /flaky-rca  {test_name, runs_url | runs[]}
  -> Fetch Run Logs        (HTTP Request)  pull the history from any CI
  -> Budget The Evidence   (Code)          extract, budget and count
  -> Flaky Pattern Detective (AI Agent + Groq + Structured Output Parser)
  -> Validate Analysis     (Code)          disbelieve the model
  -> Post to Slack  +  Send to Telegram (disabled)
  -> Respond to Caller     (the same JSON back to whoever called)
```

| Node | Type | Role |
|---|---|---|
| Flaky Test Webhook | `webhook` | `POST /flaky-rca`, responds via the last node |
| Fetch Run Logs | `httpRequest` | GETs `runs_url`; failure is survivable |
| Budget The Evidence | `code` | The interesting one — see below |
| Flaky Pattern Detective | `agent` | Holds the contract |
| Groq Chat Model | `lmChatGroq` | `openai/gpt-oss-120b` |
| RCA Schema | `outputParserStructured` | Forces the output shape |
| Validate Analysis | `code` | Checks the model's homework |
| Post to Slack | `slack` | Primary output, fails soft |
| Send to Telegram | `telegram` | Fallback, shipped disabled |
| Respond to Caller | `respondToWebhook` | Usable from a script, not just Slack |

### Budget The Evidence

Four jobs, and the agent is only trustworthy because of them:

1. **Normalise.** Accepts a bare array, `{runs}`, `{items}`, `{workflow_runs}`
   and more, from whatever CI, and reduces each run to a common shape.
2. **Extract the failure region.** Not a blind tail — it scans for lines that
   carry signal (`Error`, `Timeout`, `ECONNRESET`, `StaleElement`,
   `AssertionError`, stack frames) and keeps a window around each. A 90,000
   character log of noise with one error in it comes out as 234 characters.
3. **Fit the budget.** Caps the assembled evidence at 12,000 characters and
   divides it evenly across failing runs, so one noisy run cannot crowd out the
   other eight. Reports whether anything was dropped.
4. **Count.** Runs, failures, flakiness rate and the signature tally are all
   computed here. The model is *told* these numbers and forbidden to recompute
   them, because flakiness is a frequency claim and models miscount.

### Validate Analysis

Not a parser — the output parser already did that. This node exists to
disbelieve:

- **Every quoted line must really occur in the logs that were sent.** A
  fabricated quotation is the one failure that would make this tool worse than
  useless, because an SDET would act on it. Quotes that fail the check are
  dropped and the confidence is lowered.
- The counts are overwritten from the Budget node. The model does not get a vote.
- Enums are clamped, so an invented category becomes `Unable to Determine`.
- `pattern_frequency` is clamped to the real failure count.

## The guard rails

**One failure is never a pattern.** With fewer than two failing runs the answer
is forced to `Insufficient Runs` at Low confidence. Both the prompt and the
validator enforce this independently — tested live, and the model refuses on its
own before the validator even gets there.

**Evidence is quoted, never paraphrased.** Every claim carries a `run_id` and a
verbatim line, and the quote is checked against the input.

**Failures that do not cluster are not one bug.** If the runs failed for
different reasons the answer is `No Dominant Pattern` plus the separate
signatures, not the most impressive-looking of them.

There is also a deliberate warning in the prompt about `fix_type`: a flaky test
is not automatically a bad test. If the logs show the product intermittently
misbehaving, the answer is `Product Fix` — quarantining a test that is correctly
catching a real defect is the worst possible outcome of this analysis.

## What it produces

`dominant_pattern`, `pattern_frequency`, `category`, `evidence[]`,
`suspected_cause`, `fix_suggestion`, `fix_type`, `recommendation`, `confidence`,
`missing_information` — plus the counted fields and `validation_notes` recording
any corrections made.

Category is one of: Timing and Race Condition · Network or Timeout · Test Data
and State · Environment and Infrastructure · Selector or Locator · Test Ordering
and Shared State · Resource Exhaustion · External Dependency · Assertion
Tolerance · Unable to Determine.

Recommendation is Fix Now · Quarantine · Monitor · Not Flaky.

## Trying it without a CI

`sample_runs.json` is a synthetic history: nine runs, six failing — five sharing
a socket timeout against a payments sandbox, and one failing on an unrelated
rounding assertion, so there is a real pattern **and** a distractor to resist.

Because the webhook accepts runs inline, the whole file is a valid request body:

```bash
curl -X POST https://<your-n8n-host>/webhook/flaky-rca \
  -H "Content-Type: application/json" \
  --data @sample_runs.json
```

Expected result — this is the measured output from the live model:

```
pattern:  Network Timeout  (5 of 6 failures)
category: Network or Timeout    confidence: High    fix_type: Test Fix
tokens:   3,924 of the 8,000/minute allowance, 3.5s
```

Against a real CI, send `runs_url` instead and the HTTP node fetches the history.

## Setting it up

Import the JSON. The Groq node carries its credential by id, so it resolves on
its own. Then:

1. **Slack** — add a Slack credential and set the channel (defaults to
   `#qa-flaky-tests`). The node is set to fail soft, so a missing credential
   does *not* lose the analysis: the webhook still responds with the full JSON.
2. **Telegram** — shipped **disabled**. If you would rather not set Slack up,
   enable this node and put your chat id in it.
3. Activate the workflow to get the production webhook URL.

## Worth remembering

- **Check whether the lever exists before relying on it.** n8n's Groq node
  exposes only model, max tokens and temperature — no `reasoning_effort`. A
  reasoning model with a tight token ceiling returns *nothing*, not something
  short, and the error is an empty `failed_generation`.
- **Reasoning is billed as completion**, so "how big is the answer" is the wrong
  question. Budget for the thinking too.
- **Key a failure signature on the most severe line, not the first one.** Keying
  on the first match grouped identical timeouts under whatever DEBUG line
  happened to come first, and the pattern silently failed to cluster.
- **Never ask a model to count.** Do the arithmetic in code and hand it over.
- **Verify quotations.** If an agent cites evidence, check the citation exists —
  it is a handful of lines and it is the difference between a tool that is
  trusted and one that is not.
