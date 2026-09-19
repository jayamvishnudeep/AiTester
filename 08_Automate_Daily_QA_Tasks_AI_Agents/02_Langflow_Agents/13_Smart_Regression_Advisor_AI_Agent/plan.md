# Plan — Smart Regression Advisor (Langflow AI Agent)

| | |
|---|---|
| **Role** | SDET |
| **Problem** | Regression cycles are too long, or too blind |
| **Input** | A git diff and the codebase |
| **Output** | The list of tests worth running |
| **Shape** | Text Input → Prompt Template → LLM → Structured Output → Text Output |

## What a subset actually claims

Recommending a subset is not a summary, it is a **promise**: the tests left out
would not have caught this change. Everything about the design follows from how
that promise fails.

Run one test too many and you waste a few minutes. Run one test too few and
nothing looks wrong — the suite goes green, the recommendation looked
authoritative, and the regression ships. The output is identical in both cases.

So the impacted set is **computed, never judged**. Code parses the diff, builds
an import graph over the repository, and walks it backwards from each changed
file to the tests that reach it. A model that is approximately right about which
tests to run is worse than no advice at all, because it is wrong in the
direction nobody checks.

## Where this departs from the brief

The given shape hands a diff to a model and takes back a list of test names.
That produces plausible file names — sometimes real ones, sometimes not — with
no way to tell which. For a recommendation whose entire value is the tests it
*omits*, that is the worst possible property.

The model keeps the job it is good at: ordering the selected tests by risk, and
saying what the subset might miss. On the sample run it did the most useful
thing available to it and argued against its own subset, on the grounds that a
change to a money utility has failure modes too subtle for one checkout spec to
certify. Code cannot produce that paragraph; it also cannot be trusted to
produce the list.

## Escalation is the feature

A graph can only model what is an edge. Plenty of real changes are not:

- Nothing imports `package-lock.json`, and a dependency bump can alter behaviour
  anywhere the dependency is used.
- `config.properties` is read by name at runtime. No test imports it, so the
  graph says zero tests are affected — confidently and completely wrongly.
- `tsconfig.json` decides how every specifier resolves, so changing it
  invalidates the edges the analysis was about to rely on.
- A binary patch or a merge diff cannot be read faithfully, which yields a
  *partial* changed-file list. Partial input to a subset is worse than no input,
  because it still produces an answer.

For all of these the analyser refuses to narrow and says which rule fired.
**Escalating is not the agent failing; it is the agent working.** A tool that
always produces a small number is a tool that is lying some of the time.

## The bug that made it useless while looking fine

The file index held **unresolved** paths and the import targets held **resolved**
ones. Python dictionaries compared them as different keys, so every reverse
lookup returned an empty set.

The output of that bug was not a crash or an error. It was:

> `01_change_money_util.diff  →  0 of 5 tests (100% skipped)`

A clean, confident, well-formatted recommendation to skip the entire suite —
the exact false negative this agent exists to prevent, produced by the code
meant to prevent it. Everything is resolved consistently now, and the regression
test for it runs the analyser from a **relative** repository path, because with
an absolute one the bug cannot reproduce.

A second, milder bug in the same area: Java classes in the same package were
given edges to each other, since same-package classes need no import statement.
But visibility is not dependency — that made every test class depend on its
neighbours, so touching one page object selected every test in the package. A
same-package edge is now added only when the file actually names the class.

## Pipeline

```
Text Input (path to a diff)
  → Regression Impact Analyzer   parse the diff, index the repo, build the
                                 import graph, walk it backwards, apply the
                                 escalation rules, write impacted_tests.json
  → Prompt Template              the brief: changed files, selected tests with
                                 their trails, escalations, blind spots
  → Groq (qwen/qwen3.8-27b)      orders the work, weighs the risk; forbidden to
                                 add or remove a test
  → Regression Plan Writer       evidence, then advice, then blind spots
  → Chat Output
```

## Blind spots, printed with every plan

The list at the end of every plan is not a disclaimer, it is the part a reader
needs before trusting the subset. A static import graph cannot see a selector
matching markup, an HTTP boundary, a database migration, a value read by name at
runtime, Cucumber glue bound by regular expression, shared state between tests,
or timing.

The first of those is worth noting for where it sits: **a test id changing in a
component breaks the page object looking for it, with no edge between them** —
which is precisely the coupling agent 12 in this section exists to repair. The
two agents are blind and sighted in complementary places.

## Verified

- **111 component tests**, no Langflow or network needed, weighted towards false
  negatives: does the test still get selected through an alias, a barrel file, a
  `require`, a `.js` specifier that means `.ts`, a page object two hops away.
- **Mutation-checked, eleven defects.** Each was introduced alone to confirm the
  suite goes red: aliases ignored, the walk cut to one hop, escalations
  disabled, unreadable diffs accepted, comment-only changes treated as
  substantive, same-package edges restored, blind spots suppressed. The first
  attempt at reproducing the resolved/unresolved bug was **inert** — it only
  bites on a relative path — which is what exposed the missing test.
- **All six sample diffs run end to end** through the real flow, and the
  verdicts in the README are the ones it produced.
- **Canvas edge count re-checked after opening in the UI** — five of five.

## What this is not

It does not run the tests, measure coverage, or read history. A coverage-based
impact analysis is strictly better where coverage data exists, because it
observes real execution rather than inferring from imports. This is the version
that works with nothing but a checkout and a diff, and it says so rather than
implying more.
