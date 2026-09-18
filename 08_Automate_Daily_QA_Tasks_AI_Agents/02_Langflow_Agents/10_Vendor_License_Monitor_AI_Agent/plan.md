# Plan — Vendor License Monitor (Langflow AI Agent)

| | |
|---|---|
| **Role** | QA Lead |
| **Problem** | Paying every month for tools nobody opens |
| **Input** | Tool login activity logs |
| **Output** | "Revoke license" suggestions, costed |
| **Shape** | Input → Custom Component (inactivity filter) → Prompt Template → LLM → Report Output |

## The brief

A QA team accumulates tools. Someone trials BrowserStack for a project, four
people get seats, the project ends, and the seats renew quietly for two years.
Nobody is doing anything wrong — the information needed to notice is spread
across four admin consoles, and checking it is nobody's job.

The input is what those consoles export: who has a seat, what it costs, and
when they last logged in. The output is a list of seats worth cutting, with the
money attached.

## The failure this agent has to avoid

Every other agent in this section fails by being wrong in a document. This one
fails by being wrong about a **person**. A seat wrongly on a revoke list is a
colleague who opens BrowserStack on Monday and cannot log in.

That asymmetry sets three rules:

**The tiers are computed, not judged.** Whether an account is safe to cut
outright or needs a conversation first is decided by comparing two dates — never
used at all, or idle for at least twice the threshold, is `revoke_now`;
everything else dormant is `confirm_first`. A model asked to make that call
would make a slightly different one each run, and "slightly different" here
means a different person's name on the list.

**Nothing is suppressed silently.** An exception does not delete a finding. It
moves it to its own table, with the tier it would have been and the reason
given. An exceptions list you cannot see the effect of is indistinguishable
from a filter that is quietly broken.

**A new account is not a dormant one.** Someone who joined last week has never
logged into Confluence because they have not needed it yet. Without a grace
period the agent's first recommendation to any team is to revoke the new
starter's access, which is exactly the output that gets a tool uninstalled.

And underneath all three, the same guard every generating agent in this
repository has: **an empty input does not produce an empty answer.** Run a model
against no log and it does not say "there is no log" — it writes a plausible
revoke list naming plausible people. So the filter refuses before the model is
ever reached:

> No activity log reached this component, so anything reported from it would be
> invented - and an invented revoke list can name a real person.

## Why the arithmetic is in code

The seat cost is in the log. The saving is that number times twelve. There is
nothing here a model does better than `*` does, and three reasons it does worse:
it will produce a different total on a re-run, it will round, and — observed on
the first real run of this flow — it will confidently state `$2,048.00` for a
column that adds to `$2,016.00`.

That run is the argument for the whole design. The tables were right, because
code built them. Only the prose was wrong. The fix was to forbid the model from
producing any figure not already in the findings, and the containment is that a
model error can only ever reach the paragraph, never the table.

## What the model is actually good at here

Three things the arithmetic cannot do:

1. **Prioritising across tools.** Nine seats to revoke is a list. "Start with
   BrowserStack, it is two thirds of the money" is a plan.
2. **Noticing when the problem is the contract.** Four dormant seats out of six
   is not a seat problem, it is a licence-volume problem, and the fix is a
   conversation with the vendor rather than four revocations. The filter
   computes a `dormant_fraction` per tool precisely so the model has a number to
   notice that from.
3. **Writing it for people who will read it about themselves.** The prompt says
   so explicitly: a seat is on the list because it went unused, not because
   anyone did anything wrong.

## The Langflow constraint that shaped the wiring

Carried straight from agent 09: **a component can expose only one selected
output on the canvas.** A second wired edge works through the API and is
silently deleted the moment the flow is opened in the UI — which is worse than
failing, because the flow keeps running and the downstream node just never
receives anything.

So the filter's structured findings do not travel down a second edge. They are
written to `license_findings.json` in a shared reports folder and read back by
the writer. The file is a better answer than the edge anyway: a number in a
report is a claim, and a number in a file you can re-generate is a fact.

Building this flow turned up a second, related trap. The Chat Output's
`input_value` is a `HandleInput` — `"type": "other"`, five accepted types — and
an edge that describes it as a plain `str`/`Message` handle does not match. The
canvas drops it without an error. Four of five edges rendered and the fifth
simply was not there, which is only visible if you count them.

## Pipeline

```
Text Input (log path)
  → Inactivity Filter          parses CSV or JSON, classifies every seat,
                               computes the money, writes license_findings.json
  → Prompt Template            the brief: totals, per-tool, both tiers by name
  → Groq (qwen/qwen3.8-27b)    prioritises; forbidden to compute or invent
  → License Report Writer      reads the findings back, composes the report
  → Chat Output
```

The brief sent to the model names the accounts in **both** tiers. An earlier
version sent only a count for `confirm_first`, and the model — asked to write
about accounts it had not been shown — reported the tier as empty, directly
contradicting the table above it in the same document. Ask for something the
brief does not carry and a model will fill the gap rather than say it cannot.

## Verified

- **132 component tests**, no Langflow or network required. Every threshold is
  tested one day either side: 59/60/61 days for dormancy, 119/120/121 for the
  revoke tier, 13/14/15 for the grace period.
- **Mutation-checked.** Six plausible defects — each boundary flipped by one, a
  wrong cost multiplier, exceptions dropped instead of reported, the no-log
  guard removed — were introduced one at a time to confirm the suite fails for
  every one of them. A suite that has never gone red has not been shown to work.
- **Both sample formats** run end to end through the real flow, and the
  documented numbers are the ones the flow produced, not ones written by hand.
- **The canvas edge count was re-checked after opening the flow in the UI**,
  which is the only way the dropped-edge bug shows up.
