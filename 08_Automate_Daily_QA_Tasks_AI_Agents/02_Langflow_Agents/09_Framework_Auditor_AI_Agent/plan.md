# Plan — Framework Auditor (Langflow AI Agent)

An SDET Lead points it at an automation repository and gets back an audit: what
is in there, how much of it, where, and what to fix first.

Status: **built and verified against the live Groq API.** Both sample frameworks
audit end to end, the report's numbers are reproducible from the committed JSON,
and 79 tests cover the 27 rules.

## The brief

| | |
|---|---|
| Audience | SDET Lead |
| Problem | Technical debt accumulation in framework |
| Input | Automation repository |
| Output | Architecture recommendations |
| Helpful for | Long-term maintenance and health of the automation suite |
| Given shape | File Input (code structure) → Prompt Template (audit patterns) → LLM → Structured Output → Report Output |

## Why the model never sees the repository

A middling Selenium suite is tens of thousands of lines. Groq's free tier allows
eight thousand input tokens a minute. "Send the codebase to the model" is not an
option that exists, at any tier worth paying for, on a repository worth auditing.

That constraint turns out to point at the right design anyway, because an audit
is mostly **counting** — and counting is the thing code does exactly and a model
does approximately. So:

> **Code finds and counts every occurrence. The model decides what to do about
> them, and only that.**

The scanner walks the tree, applies a regex per rule per line, reads the versions
out of `pom.xml` and `package.json`, and produces a compact brief: totals by
rule, which dependencies are behind, and a dozen quoted lines from the worst
offenders so the advice can name a file and a line. That brief is a few hundred
tokens whether the repository is four files or four thousand.

The consequence worth noticing: **audit quality does not degrade as the
repository grows.** A tool that feeds source to a model gets vaguer the bigger
the codebase, which is exactly backwards — the big old codebase is the one that
needs auditing.

## The failure this agent has to avoid

A false positive.

Every other agent in this folder risks producing something wrong. This one risks
producing something *annoying*, which is worse for adoption. An auditor that
flags `getByRole('button', { name: 'Sign in' })` as a bad locator, or a static
factory method as shared mutable state, gets its report skimmed once and never
run again. Trust is the whole product.

So rules are deliberately narrow, and every one is tested **twice**: once on a
line it must catch, and once on the line an experienced engineer would actually
write in its place, which it must leave alone. Fifty-four of the seventy-nine tests
are that pair, one per rule.

Two rules failed their own test during development and were tightened rather than
kept:

- `static WebDriver driver;` is shared state, but `static WebDriver getDriver()`
  is a factory method. The first pattern caught both, so it now requires a `=` or
  a `;` after the name.
- Playwright writes an absolute XPath as `'xpath=/html/...'` rather than
  `'/html/...'`, so the rule missed every TypeScript case until the optional
  prefix was added.

Both were found by running the scanner against the sample frameworks and reading
what it said, which is the cheapest code review there is.

A third came from elsewhere. A fan-out of subagents was asked to propose and vet
detection rules independently; it returned 33, most of which duplicated the set
above, but nine did not — and one of its observations was that
`implicitlyWait(Duration.ZERO)` is the *remediation* for an implicit wait, not an
instance of it. The rule as written flagged the fix. The nine additions are the
ones this scanner could not have found by reading its own samples: an `expect()`
with no `await`, which is an assertion that can never fail; a `Page` held at
module scope, which is the TypeScript analogue of the static driver; and the
`new Promise(r => setTimeout(r, n))` sleep that survives any lint rule banning
`waitForTimeout`.

## The Langflow constraint that changed the design

The first build had the scanner expose two outputs — a Message brief for the
prompt, and the structured findings for the report writer — with an edge from
each. It ran correctly from the API.

Then opening the flow in the Langflow canvas **deleted one of the edges**. A
component in Langflow 1.12 has a single *selected output*; edges from its other
outputs do not survive the canvas normalising the graph. The flow worked until
somebody looked at it, which is the worst kind of broken.

So the hand-off goes through a file instead. The scanner writes
`audit_findings.json` into the reports folder and the writer reads it back. Every
node in the flow now has one output feeding one edge, which is a shape the canvas
leaves alone — verified by opening it, re-running, and re-counting the edges.

It also turned out to be better. The structured findings exist as a deliverable
whether or not the model step succeeds, and a number in a file that can be
regenerated is a fact in a way that a number inside a document is not.

## What the model is actually good at here

Prioritisation, which is the part that is genuinely a judgement:

- **Ordering by leverage rather than severity.** Given 15 hard sleeps and 3
  static drivers, it led with the static driver — fewer occurrences, but it is
  the reason the suite cannot parallelise, so fixing it unlocks everything else.
- **Estimating size.** "A medium-sized refactor touching 3 files" against "a
  mechanical replacement" is the distinction a lead needs to plan the work.
- **Saying what to leave.** Its "Leave for now" section argued that re-enabling
  two disabled tests should wait until the structural fixes land, because
  re-enabling flaky tests before then only adds noise. That is a real trade-off
  and not one a rule could state.

The report keeps the two apart on the page: the counted evidence first, then a
section that says in as many words that a language model wrote it.

## Pipeline

```
Text Input         the repository path
  -> Framework Scanner    walks it, counts, writes audit_findings.json
  -> Prompt Template      the audit brief + {findings}
  -> Groq                 qwen/qwen3.8-27b, max_tokens 900, temperature 0.2
  -> Audit Report Writer  reads the findings back, composes audit_report.md
  -> Chat Output          what was found and where the report is
```

## Verified

- Both sample frameworks audit end to end, from the node and from the API.
- 79 tests: every rule on a line it must catch and a line it must not, the
  layer-awareness rules, dependency staleness, the directories it must skip, both
  components' guards, and the scanner-to-writer hand-off.
- The flow survives being opened in the canvas — 5 edges before and after.
- The committed `reports/audit_findings.json` reproduces every number in
  `reports/audit_report.md`.
