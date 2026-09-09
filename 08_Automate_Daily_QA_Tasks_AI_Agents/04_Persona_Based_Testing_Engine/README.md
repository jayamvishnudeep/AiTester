# Persona-Based Testing Engine — n8n AI Agent

A product QA describes a feature and names the people who will use it. The
engine returns a separate test flow for each of them — what a grandparent
actually does with this screen, and where a finance officer will break it — and
writes every step into Google Sheets as a working test list.

Exported as `Persona_Based_Testing_Engine_n8n_workflow.json`. The build log is in
[`plan.md`](plan.md).

## The failure mode this is built to prevent

The three agents before this one each had an obvious way of being wrong. This
one's is quiet, and it is the reason the engine needs a guard rail at all:

**A persona test generator will happily produce the same flow five times with
different names on top.**

```
Senior Citizen:  1. Open the app  2. Log in  3. Complete the task  4. Verify
Power User:      1. Open the app  2. Log in  3. Complete the task  4. Verify
```

Nothing there is malformed. The schema passes, a human skim passes, and the
sheet fills with work nobody should do. All the value is in the *difference*
between the flows — so the difference is what gets measured.

> **Two personas that produce the same flow mean the personas were ignored.**

After every persona has been generated, the engine compares each pair of flows
and flags the run when they converge. On the live test the grandparent and the
finance officer shared **20% of their vocabulary**, well under the 60% limit.

## Every step names the trait that caused it

The field doing the real work is `driven_by`:

```
action:     Set the tablet browser zoom to 200% before loading the portal
driven_by:  low vision, runs the browser zoomed in

action:     Tab to the email field, type the parent email, Tab to the code field
driven_by:  expects keyboard navigation and shortcuts
```

That makes a step auditable — a reviewer can ask "is that true of this persona?"
and get an answer. A step that cannot name its cause is a generic step wearing a
costume, and the validator drops it.

## The pipeline

```
Webhook                POST /persona-flows  {feature, personas[]}
  -> Prepare Personas    (Code)  normalise, default library, cap the count
  -> Loop Over Personas  (splitInBatches)
       -> Pace The Loop      (Wait 35s — the rate limit)
       -> Persona Simulator  (AI Agent + Groq + Structured Output Parser)
       -> Validate Flow      (Code)  per-persona guard rails
       -> back into the loop
  -> Compare Flows       (Code)  convergence check + one row per step
  -> Append Test Flows   (Google Sheets)
  -> Send to Telegram  ->  Respond to Caller
```

| Node | Type | Role |
|---|---|---|
| Persona Webhook | `webhook` | `POST /persona-flows`, responds via the last node |
| Prepare Personas | `code` | One item per persona; applies the default library |
| Loop Over Personas | `splitInBatches` | One agent call per persona |
| Pace The Loop | `wait` | 35s — measured, not guessed |
| Persona Simulator | `agent` | Writes one persona's flow |
| Groq Chat Model | `lmChatGroq` | `openai/gpt-oss-120b` |
| Flow Schema | `outputParserStructured` | Forces the step shape |
| Validate Flow | `code` | Drops untraceable steps, flags invented controls |
| Compare Flows | `code` | The convergence check; flattens to one row per step |
| Append Test Flows | `googleSheets` | 13 columns, appended |
| Send to Telegram | `telegram` | Run summary |
| Respond to Caller | `respondToWebhook` | Full result as JSON |

**One agent call per persona, not one call for all of them.** A single call
producing five flows would be a large completion and risks truncation — and
asking for them separately stops the model averaging the personas together,
which is the convergence failure above.

**The comparison cannot happen inside the loop**, because each iteration only
sees itself. It hangs off the loop's *done* output, where every flow is
available at once.

## The rate limit is part of the design

A persona call measures at **~4,000 tokens** — 1,772 of prompt, because the
whole feature description is sent with every persona, and ~2,200 of completion.
Against Groq's free-tier ceiling of 8,000 per minute that is **two personas a
minute**, so the Wait node is **35 seconds**.

A four-persona run therefore takes about two and a half minutes. Without the
wait it fails halfway, writing two rows and missing two — which looks like it
worked, and is the worst outcome available.

## The guard rails

**1. Flows must diverge.** Pairwise overlap above 60% flags the run. Identical
flows score 100% and are named in the notes.

**2. No step without a trait.** A `driven_by` that is missing, or that merely
restates the action, drops the step. The comparison is on word stems rather than
exact text, because `"Enter the card number"` against
`"entering the card number"` is the same non-answer one suffix apart.

**3. No inventing the product.** The feature description is the only source of
what exists. A step citing a `"Save for later"` button the description never
mentions is flagged; `"Pay"` is not. What a persona needs but the feature does
not describe belongs in `gaps` as a question for the product owner — a genuinely
useful finding, where an invented button is a test that cannot be run.

**4. An empty run is visible.** If every step fails validation, the sheet gets a
`NONE` row saying so. An empty sheet reads as a feature with no risks.

## Personas

Supplied personas always win. A request with none falls back to a library of
five: Power User, First-Time User, Senior Citizen, Screen-Reader User, and
Mobile-Only on a slow connection.

That library is deliberately **not** a list of demographics. Each entry carries
traits that change what a person *does* — "less precise tapping", "needs errors
announced, not only shown in red", "requests time out and are retried" — because
those are the only traits a test step can act on. Every row records
`persona_source`, so a reader can always tell a generic archetype from a
researched persona.

## Trying it

`sample_request.json` is one feature — a school fee payment portal — and four
personas written to be genuinely different: a parent on a lunch break, a
grandparent, a school finance officer, and a parent using a screen reader.

```bash
curl -X POST "https://<your-n8n-host>/webhook-test/persona-flows" \
  -H "Content-Type: application/json" \
  --data @sample_request.json
```

Allow about two and a half minutes for four personas — the run is paced on
purpose.

Measured output for two of them:

```
Grandparent paying for a grandchild   9 steps, 100% trait-anchored, 6 gaps
School finance officer                9 steps, 100% trait-anchored, 5 gaps
cross-persona overlap: 20%   converged: false
tokens: 4,183 and 3,814
```

## Setting it up

Import the JSON. Groq, Google Sheets and Telegram all carry their credentials by
id, so nothing needs picking — the first agent in this folder where every output
node works out of the box.

Rows are appended to the existing **n8n** spreadsheet
(`163AUrBaP90RYm0dRJI...`) on a new tab, **Persona Test Flows**, alongside the
sheets `02_BugTriage` and the RCA agent already write to. Create that tab with
the 13 column headers before the first run, or point the node at your own sheet.

## Worth remembering

- **When the value is in the difference, measure the difference.** A schema
  cannot tell you the personas were ignored; comparing the outputs can.
- **Make the model show its reasoning as a field, not as prose.** `driven_by`
  turns "trust me, this is persona-specific" into something checkable.
- **Ask for fewer, better items.** Six to twelve steps truncated the response;
  five to nine returns clean and reads more like real testing work.
- **Pace loops around a rate limit deliberately.** A partial run that looks
  complete is worse than a failure that announces itself.
- **An empty result needs a row.** Silence in a QA artefact gets read as "no
  issues found".
