# Plan — Smart CI/CD Failure Analysis (Langflow AI Agent)

| | |
|---|---|
| **Role** | Automation Engineer |
| **Problem** | Twenty minutes of scrolling to find out why a build failed |
| **Input** | Jenkins / CircleCI / GitHub Actions logs |
| **Output** | A human-readable root cause analysis |
| **Shape** | Text Input → Text Splitter → Prompt Template → LLM → Text Output |

## Where this departs from the brief, and why

The brief says chunk the log and summarise the chunks. That is the obvious
design and it is the wrong one, for a reason specific to this input: **a CI log
is almost entirely noise.** The Jenkins sample here is 205 lines, of which 17
say anything about the failure. The rest is Maven downloading jars, git
plumbing, and 13 tests that passed.

Chunk that and you get roughly twenty-five chunks, of which twenty-three are
about dependency downloads. Every one costs a model call, and the one chunk
that matters is diluted into one paragraph among twenty-five. On a real log —
Jenkins consoles routinely run past 50,000 lines — it is worse than useless.

So the selection happens in code and the splitter changes job. It is no longer
how the log reaches the model; it is a **ceiling** on what reaches the model
once the extraction is done. In normal operation the brief passes through it
whole. If some pathological log produces an enormous brief, only the first
chunk goes on — which is why the brief leads with the counted summary and puts
the quoted evidence last. What survives a truncation is the top, so the top is
the part that must not be lost.

The other three answers were agreed before building: all three CI systems
rather than the two named, a report written to disk like every Langflow agent
from 07 onward, and one analysis per run with failures grouped by shared cause.

## Grouping is the whole agent

Everything else here is packaging. The thing that turns a log into an answer is
this: **twelve tests went red, and they are not twelve problems.**

Nine of them are the same `NullPointerException` in one page object method. Two
are unrelated assertion failures. One is a timeout. An engineer who knows that
fixes one method and re-runs; an engineer who does not reads twelve stack
traces.

So each matched line is normalised into a signature — numbers, timestamps, hex,
line numbers and durations stripped out, since those are exactly what differs
between two occurrences of the same failure — and grouped on it. That is
counting, and counting is what code is for. The model is never asked how many
of anything there are.

## Three ways the grouping was wrong first

All three produced output that looked fine and was wrong about the most basic
question, which is how many things broke.

**Stack frames became failures.** A frame like
`at org.openqa.selenium.support.ui.WebDriverWait.timeoutException(...)` contains
an exception class name, so it matched as a failure of its own. A single
timeout was reported as two. Fixed by consuming an anchor's continuation lines
so they cannot be anchors themselves.

**One npm error block became four.** `npm error code ERESOLVE`, `npm error
ERESOLVE could not resolve`, `npm error Could not resolve dependency:` and
`npm error Conflicting peer dependency:` are one failure printed across twenty
lines. The first fix consumed continuations only as far as the quote limit,
which is six lines — so the block split anyway. How much belongs to a failure
and how much of it is worth showing turned out to be different questions:
consumption now runs to the end of the block, quoting still stops at six.

**The runner's own summary was counted again.** Maven prints a `Results:`
block recapping every failure it already reported. Counting that too reported
twenty-four failures in a run that had twelve. The recap region is now skipped.

The result is a number that can be checked: the extractor reports 12 failures
for a run whose own summary says `Tests run: 25, Failures: 3, Errors: 9`. Those
agreeing is not a coincidence, and the test suite asserts it.

## The failure this agent has to avoid

A model asked to explain a failure it cannot see will write a fluent,
well-structured, entirely invented explanation. This agent has two guards
against that, and the second is the one that surprised me into writing it:

**No log, no analysis.** The standard guard in this repository.

**No failure, no analysis.** A log from a build that *passed* is refused. This
matters more than it sounds: passing a green build to a model and asking "why
did this fail?" does not produce "it didn't". It produces a plausible root
cause analysis of a failure that never happened, and nothing downstream can
tell it apart from a real one. The refusal says so plainly:

> This log does not contain a failure - it reports a successful build. There is
> no root cause to analyse, and a model asked for one anyway would write a
> convincing explanation of a failure that did not happen.

There is a third, quieter refusal: a run that genuinely failed but whose log
holds no recognisable error line. Guessing there would be inventing a cause
from an exit code.

## Pipeline

```
Text Input (log path)
  → CI Failure Extractor      detects the system, refuses a passing log,
                              matches / categorises / groups, writes
                              ci_findings.json
  → Character Text Splitter   the ceiling: chunk only if the brief is huge
  → Select Data (index 0)     take the head, which is where the counts are
  → Data to Message           back to text for the prompt
  → Prompt Template           the brief: counts, groups, quoted lines
  → Groq (qwen/qwen3.8-27b)   explains; forbidden to recount or invent
  → RCA Report Writer         evidence first, explanation under it
  → Chat Output
```

Nine nodes is more than any other agent here, and three of them exist for the
splitter chain. That is the cost of the ceiling being real rather than
decorative: Langflow's splitter emits a table, and getting back to a message
the prompt can take needs the two nodes after it.

## Verified

- **98 component tests**, no Langflow or network required — every category, the
  three CI formats, the grouping rules, and every refusal.
- **Mutation-checked.** Seven plausible defects — the recap skip removed,
  continuations allowed to become anchors, consumption re-bounded to the quote
  length, digits left in the signature, the passing-log refusal removed, the
  last category winning instead of the first, the first test-total line winning
  instead of the last — were introduced one at a time to confirm the suite
  fails for each. It does.
- **All three sample logs run end to end** through the real flow, and the
  numbers in the README are the ones it produced.
- **The canvas edge count was re-checked after opening the flow in the UI** —
  eight of eight, the check that caught a dropped edge on agent 10.
