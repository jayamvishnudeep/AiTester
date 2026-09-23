# Automate Daily QA Tasks with AI Agents

Agents that take over a job a tester actually does by hand every day. Where
[`07_n8n_Workflows`](../07_n8n_Workflows) was about learning the tool, this
section is about shipping something a colleague could use without being told how
it works.

| | Agent | What it replaces |
|---|---|---|
| 01 | [Screenshot to Bug Reporter](01_n8n_Agents/01_Screenshot_To_Bug_Reporter_AI_Agent) | Writing up a bug from a screenshot by hand |
| 02 | [Flaky Test RCA Analyzer](01_n8n_Agents/02_Flaky_Test_RCA_Analyzer) | Reading a dozen CI logs by eye to find what the failures share |
| 03 | [Performance Test Analyzer](01_n8n_Agents/03_Performance_Test_Analyzer) | Turning a load test CSV into something a stakeholder can act on |
| 04 | [Persona-Based Testing Engine](01_n8n_Agents/04_Persona_Based_Testing_Engine) | Testing the happy path for one imagined average user |
| 05 | [Visual Diff Explainer](01_n8n_Agents/05_Visual_Diff_Explainer) | Squinting at two screenshots trying to name what moved |
| 06 | [Swagger to API Tests](01_n8n_Agents/06_Swagger_To_API_Tests) | Writing a baseline API suite by hand from the documentation |
| 07 | [Manual to Playwright Tests](02_Langflow_Agents/07_Manual_To_Playwright_Tests_AI_Agent) | Retyping manual test cases as automation, case by case |
| 08 | [Page Object Generator](02_Langflow_Agents/08_Page_Object_Generator_AI_Agent) | Writing Page Object boilerplate from the markup by hand |
| 09 | [Framework Auditor](02_Langflow_Agents/09_Framework_Auditor_AI_Agent) | Reading a whole framework by eye to find what has rotted |
| 10 | [Vendor License Monitor](02_Langflow_Agents/10_Vendor_License_Monitor_AI_Agent) | Combing a seat list by hand to find who stopped using a tool |
| 11 | [Smart CI/CD Failure Analysis](02_Langflow_Agents/11_CI_CD_Failure_Analyzer_AI_Agent) | Scrolling a CI log for twenty minutes to find one stack trace |
| 12 | [Auto-Update Selectors (Self-Healing)](02_Langflow_Agents/12_Self_Healing_Selectors_AI_Agent) | Repointing every broken selector by hand after a restyle |
| 13 | [Smart Regression Advisor](02_Langflow_Agents/13_Smart_Regression_Advisor_AI_Agent) | Running the whole suite because nobody can prove what to skip |
| 14 | [Meeting Transcript to Requirements](02_Langflow_Agents/14_Meeting_Transcript_To_Requirements_AI_Agent) | Re-reading an hour of transcript to find what was agreed |
| 15 | [Security Test Generator](02_Langflow_Agents/15_Security_Test_Generator_AI_Agent) | A functional QA guessing at OWASP checks with no security background |

The agents live in two folders by the tool that runs them:
[`01_n8n_Agents`](01_n8n_Agents) holds 01–06,
[`02_Langflow_Agents`](02_Langflow_Agents) holds 07–15. The split tracks a real
constraint, not a preference: 07 onward each end by writing a file to disk, and
n8n Cloud runs on someone else's machine — "write a `.spec.ts`" there can only
ever mean "send you a download". Numbering stays attached to each agent across
the split, so "agent 09" means the same thing here as everywhere else in this
repo.

## 01 — Screenshot to Bug Reporter

A tester uploads a screenshot, optionally pastes the logs, and a Jira ticket
comes back with the symptom, the visual detail, expected versus actual,
severity, priority and category already written — with the screenshot attached.

Live form: <https://jayamvishnudeep.app.n8n.cloud/form/report-bug>

It is the first thing in this repo built for someone **other than its author**,
and that changes what mattered: a form and a result page a tester will trust,
guard rails so the output is never confidently wrong, and defensive parsing so a
bad model response cannot reach Jira.

See its [README](01_n8n_Agents/01_Screenshot_To_Bug_Reporter_AI_Agent) for the full walkthrough
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

See its [README](01_n8n_Agents/02_Flaky_Test_RCA_Analyzer).

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

See its [README](01_n8n_Agents/03_Performance_Test_Analyzer).

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

See its [README](01_n8n_Agents/04_Persona_Based_Testing_Engine).

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

See its [README](01_n8n_Agents/05_Visual_Diff_Explainer).

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

See its [README](01_n8n_Agents/06_Swagger_To_API_Tests).

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

See its [README](02_Langflow_Agents/07_Manual_To_Playwright_Tests_AI_Agent).

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

See its [README](02_Langflow_Agents/08_Page_Object_Generator_AI_Agent).

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

See its [README](02_Langflow_Agents/09_Framework_Auditor_AI_Agent).

## 10 — Vendor License Monitor

A tool activity export goes in; a costed list of seats worth cutting comes out —
who has not logged in, for how long, what the seat costs, and which are safe to
revoke outright rather than ask about first.

Its line between code and model is the same one as 03's, drawn where the stakes
are highest. **Code decides who is on the list and what it costs; the model only
decides what to do first.** Whether a seat is dormant is two dates subtracted,
and the saving is a multiplication — a model would answer both slightly
differently on a re-run, and "slightly differently" here means a different
colleague's name.

Its failure mode is the only one in this folder that reaches a person. Every
other agent here is wrong in a document that gets skimmed; this one is wrong by
having someone's access taken away on Monday. So a never-used account created
last week is treated as **new rather than dormant**, an exception never deletes
a finding but moves it to a table showing what it suppressed and why, and the
first real run's lesson is on the page — the model stated `$2,048.00` for a
column adding to `$2,016.00`, and the tables were right anyway, because it never
touched them.

See its [README](02_Langflow_Agents/10_Vendor_License_Monitor_AI_Agent).

## 11 — Smart CI/CD Failure Analysis

A Jenkins, GitHub Actions or CircleCI log goes in; a root cause analysis comes
out — which step failed, what broke, and which of the failures are actually the
same failure.

Its line between code and model is about **selection**, and it is the reason the
implementation departs from the obvious design. Chunking a CI log and
summarising the chunks spends the budget on noise: the Jenkins sample here is
205 lines and 17 of them say anything about the failure. So code finds the
failure region and the model never sees the log. The splitter stays, but as a
ceiling rather than as the way in.

Grouping is what it actually sells. **Twelve tests went red and they are not
twelve problems** — nine are the same `NullPointerException` in one page object,
two are unrelated assertions, one is a timeout. An engineer told that fixes one
method; an engineer not told reads twelve stack traces. The grouping is counting,
so the model never does it, and the count is checkable: the extractor reports 12
failures for a run whose own summary says `Failures: 3, Errors: 9`.

Its failure mode is the sharpest restatement of this folder's oldest lesson. Give
a model a log from a build that **passed** and ask why it failed, and it does not
answer "it didn't" — it writes a convincing analysis of a failure that never
happened. So a passing log is refused outright, as is a failed run whose log
holds no recognisable error.

See its [README](02_Langflow_Agents/11_CI_CD_Failure_Analyzer_AI_Agent).

## 12 — Auto-Update Selectors (Self-Healing)

Selectors that stopped finding their elements go in; replacements come out, each
one already run against the page and confirmed to resolve to exactly one element.

Its line between code and model is drawn by asking which half is checkable.
**Code parses the DOM, reads the old element's identity, builds candidates,
evaluates them and scores them; the model is asked only whether the element
found is the element the test meant** — a question about intent that no amount
of parsing answers. Handing the whole job to a model produces something that
looks right every time and is verifiable never, which for this task is the worst
available property.

Its failure mode is the sharpest in the folder because of how quiet it is. A
selector that resolves to *nothing* fails loudly next run and gets fixed; a
selector that resolves to the *wrong element* passes, and the suite goes on
reporting green about something it is no longer testing. So nothing is proposed
that has not been evaluated, ties are reported rather than broken, and an element
that is genuinely gone gets a refusal instead of a guess.

It also has to obey a constraint set by its neighbours: **agent 09 flags absolute
XPath, positional and styling-class selectors as anti-patterns**, so a healer
emitting them would manufacture debt another agent here reports. Healing climbs a
ladder toward test ids and accessible names, and leaves the suite more durable
than it found it.

See its [README](02_Langflow_Agents/12_Self_Healing_Selectors_AI_Agent).

## 13 — Smart Regression Advisor

A git diff goes in; the list of tests that can actually reach the changed code
comes out, each carrying the import path it was reached by — or a flat refusal
to narrow, when the change is one no graph can model.

Its line between code and model is the folder's starkest, because of what a
subset claims. **Recommending a subset is a promise that the skipped tests could
not have caught the change**, and the two ways of being wrong are not
symmetrical: one test too many costs minutes, one test too few is silent. So the
set is computed from the repository's own import graph and the model never
touches it; the model orders the work and weighs the risk of the skip. On the
sample run it used that freedom to argue *against* its own subset, which is
exactly the judgement code cannot produce.

**Escalating is the feature, not the failure.** Nothing imports a lockfile; a
`.properties` file is read by name at runtime; a `tsconfig` change invalidates
every edge the analysis was about to use. For those the honest answer is "run
everything", and a tool that always returns a small number is lying some of the
time.

Its instructive bug is the one that looked like success: an index of unresolved
paths against import targets of resolved ones meant every reverse lookup
returned nothing, and the agent cheerfully recommended skipping **100%** of the
suite. The regression test for it uses a relative repository path, because with
an absolute one the bug cannot reproduce.

See its [README](02_Langflow_Agents/13_Smart_Regression_Advisor_AI_Agent).

## 14 — Meeting Transcript to Requirements

A Zoom or Teams transcript goes in; the requirements, action items and decisions
it actually contains come out as Jira payloads, each quoting the line somebody
said it in.

Its line between code and model is drawn somewhere new for this folder. Reading
a conversation **is** a language problem, so the model does more of the real work
here than anywhere else in the section. What code keeps is the part that can be
checked: **every item must quote a transcript line verbatim, and every quote is
verified against the transcript before the item is allowed through.** The model
may propose; only code may confirm. Attribution is taken from the matched turn,
so the model says what was agreed and the transcript says who said it.

Its failure mode is the least visible in the folder. A requirement nobody said
does not look like a bug — it looks like a tidy ticket, phrased exactly like the
real ones, describing the sensible thing the team *would* have agreed. Nobody
reading the list can pick it out, and the meeting is over. Handed three invented
requirements written in the same register as the real ones, the verifier rejected
all three, because an invented requirement has nothing to quote.

It also holds the line between **agreed and merely discussed**. Someone floating
an idea that the group declines is recorded as a decision not to do it, not as a
requirement to do it — and a meeting that agreed nothing produces an empty list
that says so.

See its [README](02_Langflow_Agents/14_Meeting_Transcript_To_Requirements_AI_Agent).

## 15 — Security Test Generator

An API spec goes in; the OWASP injection and access-control checks worth
running against it come out — every check aimed at a parameter that actually
exists, every payload the standard published detection probe for its class.

Its line between code and model is drawn at the point where a wrong answer
stops being a report problem and becomes a live action. **The payloads are a
fixed, hand-verified catalog the model never writes to** — an invented
injection string is a security-testing action with no reviewer, unlike an
invented test case or an invented selector elsewhere in this folder. The model's
only decision is which of the checks *already found* to run first.

Its targeting is the part worth trusting rather than skimming. SSRF and open
redirect fire only on a parameter shaped like a URL; path traversal only on one
shaped like a file path; XXE only on a literal XML body; BOLA only on an id in
the path or query. A report that offers every attack on every field gets read
once, and the whole value of a security report is being read twice.

It also carries the folder's most direct guard rail: **every report opens with
a fixed authorised-testing disclaimer that the model cannot write around**,
because the one acceptable use of an attack-payload generator is testing
something you have permission to test.

See its [README](02_Langflow_Agents/15_Security_Test_Generator_AI_Agent).

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
- **A Langflow edge must describe the target field exactly as the node declares
  it.** Chat Output's `input_value` is a `HandleInput` — `"type": "other"`, five
  accepted types — and an edge calling it a plain `str`/`Message` handle is
  dropped by the canvas with no error at all. Count the edges after opening a
  generated flow; four of five drawn looks identical to five.
- **Ask a model about data you did not send it and it will report it as
  absent.** A brief that carried only a *count* for one group produced a
  confident "there are none", contradicting the table printed directly above it.
  If the prompt asks for something by name, the brief has to carry the names.
- **How much belongs to a finding and how much of it to show are different
  questions.** Capping both at the same number split one twenty-line npm error
  block into four separate "failures". Consume to the end of the block; quote
  the first few lines.
- **A tool's own summary is not more findings.** Maven reprints every failure in
  a `Results:` block at the end, so counting it too reported twenty-four
  failures in a run that had twelve. Whatever parses a log has to know which
  regions are recaps.
- **Two parsers means two incompatible notions of "this element".** Using lxml
  for XPath and BeautifulSoup for CSS looks like using each library for its
  strength; in fact an element found by one cannot be recognised by the other.
  One engine, and translate into it — declining what will not translate, since a
  half-translated selector resolves to the wrong thing rather than failing.
- **Read identity from the selector's subject, not from the whole string.** In
  `#summary > div:nth-child(4) > span.value` the element addressed is the span.
  Reading the id from anywhere in the string finds `summary` and heals
  confidently onto the wrong element.
- **Mutation-test the guarantee you advertise.** A suite that passes first time
  has not been shown to work. Seven deliberate defects found two real holes,
  and one was the single property the whole agent is sold on.
- **A mutation that survives is not always a missing test.** Sometimes it is an
  *inert* mutation — the defect it reintroduces cannot bite under the conditions
  the tests run in. Reproducing a path-resolution bug needed a relative path;
  every test used an absolute one, and finding that out was worth more than the
  mutation itself.
- **Resolve paths once, at the boundary.** An index of unresolved paths against
  targets of resolved ones compares as different keys, so lookups return empty
  rather than failing. In an agent that recommends what to skip, that surfaces
  as a confident "nothing is affected".
- **Visibility is not dependency.** Java classes in a package need no import to
  see each other, but giving every pair an edge makes each test depend on its
  neighbours and selects the whole package.
- **Make the model cite, then check the citation.** Requiring a verbatim quote
  turns "did the model invent this?" from a judgement into a lookup. An invented
  claim can only carry an invented quote, and an invented quote is not in the
  source.
- **A quote has to be long enough to prove something.** Three words of ordinary
  English appear in almost any document, so a short quote lets an invented claim
  borrow a real line's attribution and pass the check.
- **Some decisions are too live to leave to a model, even with verification.**
  Everywhere else in this folder, checking a claim after the fact is enough.
  A security payload is different — sending it IS the action, so the catalog
  itself has to be fixed and reviewed, not generated and then checked.
