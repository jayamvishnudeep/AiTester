# Plan — Persona-Based Testing Engine (n8n AI Agent)

A product QA describes a feature and names the people who will use it. The
engine returns a separate test flow for each of them — what a Senior Citizen
would actually do with this screen, and where a Power User would break it.

Status: **built, tested against the live Groq API, and proven end to end on n8n
Cloud.** Thirty-seven assertions pass, including two real persona generations,
and a live four-persona run completed in 3m 5.5s. See *Proven end to end* below.

## The brief

| | |
|---|---|
| Audience | Product QA |
| Problem | Testing lacks real-user diversity |
| Input | User personas, feature description |
| Output | Test flows mimicking specific user types |
| Helpful for | Ensuring UX works for different demographics, not just the happy path |
| Given shape | Webhook → AI Agent (persona simulator) → Loop (per persona) → Structured Output → Google Sheets |

## The failure mode this agent has to avoid

The first three agents in this folder each had one way of being confidently
wrong. This one's is different and much easier to miss.

**A persona test generator will happily produce the same flow five times with
different names on top.**

```
Senior Citizen:  1. Open the app  2. Log in  3. Complete the task  4. Verify
Power User:      1. Open the app  2. Log in  3. Complete the task  4. Verify
```

Both look like output. Neither is worth anything, and nothing about the JSON is
malformed — a schema check passes, a human skim passes, and the sheet fills up
with work nobody should do. The whole value of the agent is in the *difference*
between the flows, so the difference is what has to be verified.

Which gives this agent its central rule:

> **Two personas that produce the same flow mean the personas were ignored.**

The validator measures how much each pair of flows overlaps and flags the run
when they converge. That is a computable check on the one property that matters,
and it is the analogue of the quotation check in `02_` and the figure check in
`03_`.

## Design decisions

**Every step must name the trait that caused it.** Each generated step carries a
`driven_by` field pointing at a specific persona attribute — "low vision",
"uses keyboard only", "expects keyboard shortcuts", "on a 3G connection". A step
that cannot name its cause is a generic step wearing a costume, and the schema
makes writing one awkward.

**The feature description is the only source of what the product does.** The
model may not invent screens, buttons or flows the description does not mention.
Where a persona needs something the feature does not describe, that is a
**finding**, not an assumption — it goes in `gaps` as a question for the product
owner. The standing rule from `01_LLM_Basics`, applied here.

**One agent call per persona, not one call for all of them.** Two reasons. A
single call producing five flows would be a large completion and risks the
truncation seen in `02_`; and asking for them separately stops the model
averaging the personas together, which is exactly the convergence failure above.

## The rate limit shapes the loop

Groq's free tier allows **8,000 tokens per minute**, and a single persona call
measures at **~4,000** — 1,772 of prompt, because the whole feature description
is sent with every persona, and ~2,200 of completion. That is **two personas per
minute** before the loop starts collecting 429s.

So the loop carries a **Wait node set to 35 seconds**, taken from that
measurement rather than guessed. A four-persona run therefore takes about two
and a half minutes. Without it the run fails halfway with two rows written and
two missing — the worst outcome, because it looks like it worked.

## The pipeline

```
Webhook              POST /persona-flows  {feature, personas[]}
  -> Prepare Personas   (Code)   validate, apply the default library, cap the count
  -> Loop Over Personas (splitInBatches v3)
       -> Persona Simulator (AI Agent + Groq + Structured Output Parser)
       -> Validate Flow    (Code)   guard rails, one item per step
       -> Wait             (rate limit)
       -> back into the loop
  -> Compare Flows     (Code)   convergence check across all personas
  -> Append to Sheets  (Google Sheets)
  -> Send to Telegram  ->  Respond to Caller
```

The loop's "done" output carries every flow, which is where the cross-persona
comparison happens — it cannot be done inside the loop, because each iteration
only sees itself.

## Where the output goes

Google Sheets, and for once the credential already exists: the same
`163AUrBaP90RYm0dRJI_lVaFkkneT4TyMMMeeHSwfJ0I` spreadsheet ("n8n") that
`02_BugTriage` and the RCA agent write to, with a new tab. No new credential,
nothing to pick on import.

Telegram carries a short summary — how many personas, how divergent the flows
were, and any gaps found — because a sheet nobody opens is not a notification.

## What the model produces per persona

```
persona_name
persona_summary        one line, in the model's own words, proving it read the persona
primary_goal           what this person is actually trying to achieve
steps[]                { step_no, action, expected, driven_by, risk }
friction_points[]      where this persona is likely to struggle, and why
accessibility_notes    only when the persona implies them
gaps[]                 what the feature description does not say that this persona needs
priority               High | Medium | Low - how important this persona is to test
```

`driven_by` is the field doing the real work. It is what makes a step auditable:
a reviewer can ask "is that true of this persona?" and get an answer.

## The guard rails

**1. Flows must diverge.** After the loop, the comparison node measures the
overlap between every pair of persona flows. Two flows sharing most of their
actions means the personas were ignored, and the run is flagged rather than
quietly written.

**2. No step without a trait.** Any step whose `driven_by` is missing, empty or
merely restates the action is dropped and counted. A flow that loses most of its
steps this way is reported as generic.

**3. No inventing the product.** Steps referring to screens or controls the
feature description never mentions are flagged. The honest place for "this
persona would need a confirmation screen" is `gaps`, not `steps`.

## Decisions taken

Both open questions were answered before building.

**1. One row per test step.** Thirteen columns — run id, feature, persona,
persona source, priority, step number, action, expected, `driven_by`, risk,
primary goal, accessibility notes, generated at. The sheet is a working test
list that can be filtered by persona and assigned, rather than a document.

**2. A default persona library, overridden by anything supplied.** Power User,
First-Time User, Senior Citizen, Screen-Reader User, and Mobile-Only on a slow
connection. Deliberately not a list of demographics: each carries traits that
change what a person *does*, because those are the only traits a test step can
act on. Every row records `persona_source` so a reader can tell generated
archetypes from researched personas.

## What was found by building it

**The flow size had to come down.** The first live run asked for six to twelve
steps with a 3,000-token ceiling, and both personas returned truncated JSON —
gpt-oss reasons before answering and that reasoning is billed as completion, the
same trap as `02_` and `03_`. Five to nine steps and a 5,000-token ceiling
produce clean output at ~2,200 completion tokens. Fewer, better steps also read
more like something a QA would actually run.

**The measured cost sets the Wait, and it is longer than estimated.** The plan
guessed ~2,400 tokens per persona; the measurement is **~4,000** — 1,772 of
prompt (the feature description is sent with every persona) and ~2,200 of
completion. Against 8,000 per minute that is two personas a minute, so the Wait
node is **35 seconds**, not the 20 originally written. A four-persona run takes
about two and a half minutes, and the alternative is 429s halfway through with
some rows written and some missing.

**An echo check has to compare word stems, not text.** The first version of the
`driven_by` guard rejected a value only when it matched the action exactly. It
waved through `action: "Enter the card number"` with
`driven_by: "entering the card number"` — the same non-answer, one suffix apart.
It now counts how many significant words of `driven_by` appear in the action by
five-character prefix, and drops the step above 80%.

## Test result

Both Code nodes and the comparison node are executed with mocked n8n globals,
and two real Groq calls are made with the real system message. **Thirty-seven
assertions, all passing.**

The number that matters is the cross-persona overlap. Given the same feature,
the Grandparent and the School finance officer produced flows sharing
**20% of their vocabulary** — comfortably below the 60% convergence limit:

```
Grandparent paying for a grandchild   9 steps, 100% trait-anchored, 6 gaps
  1. Set the tablet browser zoom to 200% before loading the portal
     driven_by: low vision, runs the browser zoomed in

School finance officer                9 steps, 100% trait-anchored, 5 gaps
  1. Tab to the email field, type the parent email, Tab to the code field
     driven_by: expects keyboard navigation and shortcuts

cross-persona overlap: 20%   converged: false
tokens: 4,183 and 3,814
```

Those are recognisably different pieces of testing work, which is the entire
point of the engine.

The guard rails were tested by attacking them: two identical flows are caught at
100% overlap and reported; a step with an empty `driven_by` is dropped; a step
citing a `"Save for later"` button the feature description never mentions is
flagged while `"Pay"` is not; and a run where every step fails validation writes
a visible `NONE` row rather than an empty sheet, because an empty sheet reads as
a feature with no risks.

## Proven end to end

Run against the live workflow on n8n Cloud with `sample_request.json` — four
supplied personas against the school fee payment portal:

```
duration     3m 5.5s        tokens        17,500
personas     4              test steps    35
overlap      31%  (Parent on a lunch break / Parent using a screen reader)
converged    false          steps dropped none reported
```

Every node ran green. `Prepare Personas` emitted 4 items, the loop carried 4
through `Pace The Loop` (35.001s each), `Persona Simulator` and `Validate Flow`,
and `Compare Flows` flattened them into 35 rows. Telegram delivered the summary.

**The webhook response cannot survive the run, and that is structural.** The
`curl` returned **HTTP 524 at 126 seconds** — Cloudflare's timeout in front of
n8n Cloud, returning its own error page — while the execution carried on to
3m 5.5s and finished normally. Four personas spend 140 seconds in the Wait node
alone and `MAX_PERSONAS` is 6, so no amount of tuning fits a full run inside the
proxy window.

The fix is to acknowledge on receipt: a Respond to Webhook node straight after
`Prepare Personas` returning the `run_id`, with results arriving by Sheets and
Telegram. Cutting the wait is the wrong trade — 35s comes from measured token
cost, so it buys a 429 in place of a 524.

This is the general lesson from the run: **the waits that make a paced workflow
correct are the same waits that push it past a proxy timeout.** A workflow
measured in minutes should not be holding an HTTP connection open at all.

**A finding on the reporting, not the flows.** The run note reads
`named things the feature description does not mention: Parent on a lunch break,
Grandparent paying for a grandchild, Parent using a screen reader` — those are
persona names. `Compare Flows` maps the offending flows to `persona_name` but
never carries through each flow's `invented_names`, so the note says who tripped
guard rail 3 without saying what they named. It is unactionable as written and
is a one-line fix, left in place here so the README screenshot matches the
current export.

The four flows themselves came back at 9, 8, 9 and 9 steps, all priority High,
raising six gaps between them — every one traceable to a supplied trait rather
than to the feature description.

## Deliverables

```
04_Persona_Based_Testing_Engine/
├── plan.md
├── Persona_Based_Testing_Engine_n8n_workflow.json
├── sample_request.json
├── 04_Persona_Based_Testing_Engine.png
├── Reporting_To_Telegram.jpg
└── README.md
```

## Deliberately not in v1

- **No test automation code.** The output is flows a human executes or adapts.
  Generating Playwright from a persona guess would dress speculation up as
  something runnable.
- **No persona storage.** Personas arrive per request; a library of the
  organisation's real personas belongs in a sheet of its own, and that is v2.
- **No execution or results tracking.** This produces the tests, it does not run
  them or record whether they passed.
