# Root Cause Analysis (RCA) AI Agent — n8n

Detects new production bugs in Jira, generates a structured Root Cause Analysis
with an AI agent, and writes one row per ticket into a Google Sheet styled to
mirror an Excel RCA template.

The interesting thing in this folder is that **one spec was handed to two
different builders**, and they made different calls. Both exports are here.

The spec is `resource/rca-automation-n8n-prompt.md.md`.

## Built by Claude

![The Claude-built workflow: schedule trigger, Jira search, batch loop, sheet dedupe check, an IF, normalize, OpenAI, a JSON parser and the sheet write](Root%20Cause%20Analysis%28RCA%29%20AI%20Agent%20created%20by%20claude_screenshot.png)

`Root Cause Analysis(RCA) AI Agent created by Claude.json` — 12 nodes.

```
Every 15 Minutes (schedule)
  -> Search Production Bugs in Jira   (getAll, returnAll, the spec's JQL)
  -> Loop Over Issues                 (splitInBatches)
  -> Check If Already In Sheet        (googleSheets)
  -> Already Processed?               (if) -> Skip (noOp)
  -> Normalize Jira Fields            (set)
  -> Generate RCA (AI)                (openAi, gpt-4.1)
  -> Parse RCA JSON                   (code)
  -> Append or Update RCA Row         (googleSheets)
```

It took the spec's **documented fallback** rather than its first choice: a
Schedule Trigger polling every 15 minutes plus a Jira "Get Many Issues" using
the same JQL, which the spec offers for instances where a native event trigger
is not available. Two sticky notes on the canvas carry the setup instructions.

Deduplication is explicit and visible — look the key up in the sheet, branch on
an IF, and no-op if it is already there. The model's JSON is parsed in a Code
node rather than trusted.

## Built by the n8n AI Assistant

![The n8n-Assistant-built workflow: a Jira trigger, normalize and dedupe code nodes, an agent with a structured output parser and a fixing model, a fallback row path, and a weekly XLSX export](Root%20Cause%20Analysis%28RCA%29%20AI%20Agent%20created%20by%20n8n%20AI%20Assistant_screenshot.png)

`Root Cause Analysis(RCA) AI Agent created by n8n AI Assistant.json` — 16 nodes.

```
Jira Production Bug Event (jiraTrigger)
  -> Normalize Jira Issue    (code)
  -> Lookup Existing RCA Row (googleSheets)
  -> Decide Process or Skip  (code)
  -> Should Generate RCA?    (if) -> Skip (noOp)
  -> Generate RCA            (agent + chat model + structured output parser + fix model)
  -> Build RCA Row           (code) -> Append or Update RCA Row
                             \-> Build Fallback Row (code) -> Append or Update Fallback Row

Weekly Export Schedule (schedule) -> Export RCA Sheet as XLSX (googleDrive)
```

It went for the spec's **first choice**, a native `jiraTrigger` firing on issue
events, so there is no polling delay. It also built two things the Claude version
left out: an explicit **fallback row** path, so a ticket that fails RCA
generation still lands in the sheet rather than vanishing, and the spec's
**optional weekly XLSX export** to Google Drive.

Where Claude parsed the model output in a Code node, this one uses a structured
output parser with a second model attached to repair malformed output.

## What the comparison teaches

| | Claude | n8n AI Assistant |
|---|---|---|
| Trigger | Schedule, every 15 min (the fallback) | Native Jira event trigger |
| Nodes | 12 | 16 |
| JSON safety | Code node parses defensively | Output parser + auto-fixing model |
| Failure path | Ticket is skipped | Fallback row still written |
| Optional export | not built | weekly XLSX to Drive |

Neither is simply better. The event trigger is the right answer when the Jira
plan supports it and the wrong answer when it does not — which is exactly why
the spec named a fallback, and exactly the judgement a builder has to make.
The Claude build is smaller and its dedupe logic is readable straight off the
canvas; the Assistant build is more complete and degrades better.

The reusable lesson: **write the fallback into the spec**. Both builds are
defensible because the spec said what to do when the preferred option is
unavailable.

## Setting it up

Neither export is runnable as-is — both carry the spec's placeholder JQL:

```
project = "YOUR_PROJECT_KEY" AND issuetype = Bug AND (environment ~ "Production"
  OR labels = "production" OR priority in (Highest, High)) AND status != Done
```

So before a first run:

1. Replace `YOUR_PROJECT_KEY` with a real project.
2. Attach credentials — Jira Software Cloud, OpenAI, Google Sheets, plus Google
   Drive for the Assistant version's export.
3. Point the Sheets nodes at your own spreadsheet, keyed on the Jira key so
   reruns update rather than append.

Both are exported inactive.

## Worth remembering

- **Dedupe against the destination, not the source.** Both builds look the key
  up in the sheet before spending a model call. That is what makes a polling
  workflow safe to run every 15 minutes.
- **A schedule trigger plus `getAll` is the universal fallback** for any event
  trigger your plan does not offer.
- **Never let a model's JSON reach a destination unparsed** — whether by a Code
  node or an output parser is a style choice; skipping it is not.
