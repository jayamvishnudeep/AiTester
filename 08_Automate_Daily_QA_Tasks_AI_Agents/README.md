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
| 07 | [Manual to Playwright Tests](07_Manual_To_Playwright_Tests_AI_Agent) | Retyping manual test cases as automation, case by case |
| 08 | [Page Object Generator](08_Page_Object_Generator_AI_Agent) | Writing Page Object boilerplate from the markup by hand |
| 09 | [Framework Auditor](09_Framework_Auditor_AI_Agent) | Reading a whole framework by eye to find what has rotted |

Agents 01 to 06 are n8n workflows. **07, 08 and 09 are Langflow**, because each
of them ends by writing a file to disk — and n8n Cloud runs on someone else's
machine, where "write a `.spec.ts`" can only ever mean "send you a download".

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

## 07 — Manual to Playwright Tests

Manual test cases go in, as a tester wrote them; a Playwright spec file in
TypeScript comes out, on disk, one per feature.

Its line between code and model is about packaging. **The model writes the code;
code decides what the file is called, where it goes, and what counts as code at
all.** A model asked for a test file returns one wrapped in things that are not a
test file — a fence, a "Here you go:", sometimes a closing paragraph explaining
what it wrote. None of that compiles, and a regular expression is perfect at
removing it.

Its failure mode is the sharpest in the folder, because it looks exactly like
success: run the flow with **no** steps and it does not return nothing. It
returns fluent, well-formed, entirely fictional login tests. So the input runs
to the writer as well as to the prompt, and the writer refuses to write when no
steps arrived. What gets checked is not "did it produce code" but whether every
literal in the manual case — the email, the password, the exact expected message
— survived into the output.

See its [README](07_Manual_To_Playwright_Tests_AI_Agent).

## 08 — Page Object Generator

An HTML snapshot goes in; a Playwright Page Object class in TypeScript comes
out, named after the class it contains.

Naming is its rule. **The model writes the class; the code names the file after
the class it actually found.** A Page Object file is named for the class inside
it, and a model asked to produce both will occasionally disagree with itself —
naming the file `Login.ts` while writing `class SignInPage`. Deriving the name
from the thing being named is the one rule that cannot be wrong.

Its failure mode is inventing elements. A Page Object is a promise that these
locators exist on that page, and a class with a `rememberMeCheckbox` the page
does not have compiles, reads well, and fails later as a timeout that looks like
flakiness. So the check is mechanical: pull every string out of `getByLabel`,
`getByText`, `getByTestId` and `getByRole(..., { name })`, and require each one
to appear in the source markup.

See its [README](08_Page_Object_Generator_AI_Agent).

## 09 — Framework Auditor

A path to an automation repository goes in; an audit report comes out — what
anti-patterns are in there, how many, where, which dependencies have rotted, and
what to fix first.

Its constraint is the folder's oldest one, at its sharpest. A middling Selenium
suite is tens of thousands of lines and Groq's free tier allows eight thousand
input tokens a minute, so **the model never sees the repository at all**. Code
walks the tree and counts; the model is handed the totals and a dozen quoted
lines. The useful consequence is that audit quality does not decay as the
codebase grows, which is the opposite of what happens when source is fed to a
model — and the big old codebase is the one that needed auditing.

Its failure mode is different from every other agent here. The others risk being
wrong; this one risks being **annoying**, which is worse for adoption. An auditor
that flags a good locator gets skimmed once and never run again, so every rule is
tested twice — on a line it must catch, and on the line a competent engineer
would write instead, which it must leave alone.

See its [README](09_Framework_Auditor_AI_Agent).

## What this section adds over `07_n8n_Workflows`

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
- **An empty brief does not produce an empty answer.** Give a model no input and
  it fills the gap with something plausible and completely invented — the one
  output worse than an error, because it looks like success. Where an agent
  writes a file, the writer should see the original input too, and refuse.
- **A literal `{` in a Langflow prompt is a template variable.** An
  `import { test, expect }` line in the instructions stops the flow from
  building until the braces are doubled.
- **Name generated files from the code, not from the model's opinion of it.**
  The class, the feature, the thing being named — anything derived from content
  cannot drift out of step with it.
