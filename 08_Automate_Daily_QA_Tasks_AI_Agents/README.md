# Automate Daily QA Tasks with AI Agents

Agents that take over a job a tester actually does by hand every day. Where
[`07_n8n_Workflows`](../07_n8n_Workflows) was about learning the tool, this
section is about shipping something a colleague could use without being told how
it works.

| | Agent | What it replaces |
|---|---|---|
| 01 | [Screenshot to Bug Reporter](01_Screenshot_To_Bug_Reporter_AI_Agent) | Writing up a bug from a screenshot by hand |
| 02 | [Flaky Test RCA Analyzer](02_Flaky_Test_RCA_Analyzer) | Reading a dozen CI logs by eye to find what the failures share |
| 03 | [Performance Test Analyzer](03_Performance_Test_Analyzer) | Turning a load test CSV into something a stakeholder can act on |
| 04 | [Persona-Based Testing Engine](04_Persona_Based_Testing_Engine) | Testing the happy path for one imagined average user |
| 05 | [Visual Diff Explainer](05_Visual_Diff_Explainer) | Squinting at two screenshots trying to name what moved |
| 06 | [Swagger to API Tests](06_Swagger_To_API_Tests) | Writing a baseline API suite by hand from the documentation |

## 01 — Screenshot to Bug Reporter

A tester uploads a screenshot, optionally pastes the logs, and a Jira ticket
comes back with the symptom, the visual detail, expected versus actual,
severity, priority and category already written — with the screenshot attached.

Live form: <https://jayamvishnudeep.app.n8n.cloud/form/report-bug>

It is the first thing in this repo built for someone **other than its author**,
and that changes what mattered: a form and a result page a tester will trust,
guard rails so the output is never confidently wrong, and defensive parsing so a
bad model response cannot reach Jira.

See its [README](01_Screenshot_To_Bug_Reporter_AI_Agent) for the full walkthrough
and screenshots.

## 02 — Flaky Test RCA Analyzer

An SDET points it at a test that keeps flapping. It reads several runs' logs,
finds what the failures share — `Network Timeout`, a stale locator, a
shared-state collision — and returns a named cause, the lines it read that from,
and a concrete fix.

Where agent 01 reads **one** artefact and describes it, this one reads **many**
and has to find what they have in common. That makes the token budget, not the
model, the binding constraint: Groq's free tier allows 8,000 tokens a minute and
that ceiling is on *input*, so choosing which log lines matter is done in code.
The counting is too — flakiness is a frequency claim, and models miscount.

Its guard rail is the direct analogue of 01's refusal to invent repro steps:
**one failing run is a stack trace, not a pattern.**

See its [README](02_Flaky_Test_RCA_Analyzer).

## 03 — Performance Test Analyzer

A JMeter or k6 CSV goes in; a one-page executive summary comes out — Pass or
Fail, what broke, at what load, and what it means for people who will never read
a percentile table.

Its rule is that **code decides Pass or Fail and the model only explains it**. A
verdict is arithmetic against a threshold, and this output goes to stakeholders
who cannot check it. The model's job is translation: *"One in fifty checkout
attempts took more than 4 seconds."*

Scale forced the other decisions. A one-hour run at 200 rps is ~720,000 rows,
past n8n's payload limit and any token budget, so percentiles come from a
single-pass histogram and the model never sees a row.

See its [README](03_Performance_Test_Analyzer).

## 04 — Persona-Based Testing Engine

A feature description and a set of personas go in; a separate test flow for each
persona comes out, one row per step in Google Sheets.

Its failure mode is quieter than the others: a persona generator will happily
produce the same flow five times with different names on top, and nothing about
that output is malformed. So the engine measures the **overlap between every
pair of flows** and flags the run when they converge — a computable check on the
one property that matters. Every step also names the persona trait that caused
it, which turns "trust me, this is persona-specific" into something a reviewer
can verify.

See its [README](04_Persona_Based_Testing_Engine).

## 05 — Visual Diff Explainer

Two screenshots go in, a plain-English explanation of what changed comes out,
and lands as a comment on the Jira ticket.

Its failure mode is the most seductive in the folder: a vision model asked
"what changed?" will always find something, so two identical screenshots
produce a confident paragraph about spacing and shade. Whether two files are
identical is not a judgement call, so the workflow settles it in code and
skips the model entirely.

It also carries the folder's most useful negative result. The model that was
right for agent 01 called two genuinely different screenshots identical here;
a side-by-side probe picked a better one. And its detection floor is measured
and documented rather than assumed - it catches text changes and misses small
colour shifts.

See its [README](05_Visual_Diff_Explainer).

## 06 — Swagger to API Tests

An OpenAPI spec goes in; a Postman collection and a RestAssured JUnit class
come out, covering every operation.

Its line between code and model is the sharpest in the folder: **everything
the spec determines is generated in code, and the model only adds what a
schema cannot imply**. A test derived from the document is correct by
construction; an invented endpoint is a test that 404s on its first run. That
split also makes coverage independent of the token budget, because the
deterministic tests cost nothing to generate however large the spec is - five
operations in the sample produce 19 tests before the model is called at all.

What the model adds is the part a schema cannot state: cancel an order twice,
fetch one belonging to another customer, check a limit does not pad. Those
ship as documented stubs rather than as requests pretending to be runnable.

See its [README](06_Swagger_To_API_Tests).

## What this section adds over 07

**The contract ships inside the workflow.** No instructions typed into a chat
box. The prompt, the taxonomies and the refusal rules all live in the exported
JSON, so importing it is enough.

**Guard rails, not just prompts.** A screenshot cannot show how someone got
there, so steps to reproduce are never invented — the field reads
`Not Provided - tester to complete` and confidence drops to Low. This is the
`01_LLM_Basics` anti-hallucination rule enforced at the point it would actually
do damage.

**Defensive parsing.** The model returns JSON as a string; it is parsed,
validated against a schema and every missing field defaulted before anything
reaches Jira. A malformed response is treated as a normal case, not an
exception.

**A UI a tester sees.** A styled upload form and a custom confirmation page
served through the Form Ending, rather than n8n's default success screen — with
the ticket key, a link straight to the issue, and an honest list of what the
model could not determine.

## Things learned here worth reusing

- **Binary data does not survive a Code or HTTP node in n8n.** Whatever file
  entered the workflow is gone by the time a later node wants it. Read it back
  off the trigger and re-emit it.
- **Check the rate limit that actually binds.** Groq's free tier runs out of
  output tokens per minute long before it runs out of requests per day, and it
  counts the ceiling you request rather than what you use.
- **Turn reasoning off on a thinking model when you want JSON.** Left on, the
  whole completion budget goes to reasoning and the JSON comes back truncated.
- **Read the tool's own source before styling it.** n8n's form template reads a
  CSS variable it never defines, and guessing at selectors matched the wrong
  elements.
