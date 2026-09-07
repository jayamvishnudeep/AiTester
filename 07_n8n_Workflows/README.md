# n8n Workflows

Four AI agents built in n8n, in the order they were built. Each folder has its
own README with the detail; this page is the map and the through-line.

| | Folder | What it does | Shape |
|---|---|---|---|
| 01 | [Jira AI Agents](01_Jira_n8n_AI_Agents) | Read a Jira ticket, write a test plan or strategy into Google Docs | Agent + tools |
| 02 | [Bug Triage AI Agent](02_BugTriage_n8n_AI_Agent) | Triage every Jira issue into a 25-column Google Sheet | Agent + tools |
| 03 | [RCA AI Agent](03_RCA_n8n_AI_Agent) | Detect production bugs and generate a root cause analysis | Pipeline, built twice |
| 04 | [Daily LinkedIn Post](04_Daily_LinkedIn_post_telegram_approval) | Write and illustrate a daily post, approve it in Telegram, publish | Pipeline with a human gate |

## The through-line

Read in order, these four are one story about moving instructions out of the
chat box and into the workflow.

**01 — the shape works, the prompt does not exist.** Three near-identical
workflows: chat trigger, agent, model, memory, a Jira tool and an output tool.
They run, but the AI Agent nodes carry no system message at all — every
instruction was typed into the chat at run time and never saved, so nobody else
can reproduce the result.

**02 — the prompt becomes a contract.** The same agent shape, but the folder
holds two versions of the prompt and the difference is the lesson. The first is
a persona that teaches judgement; the second adds a mandatory execution order,
verbatim tool names and a per-issue write loop, which is what turns *describing*
the work into *doing* it. This is also where the severity/priority/category
vocabularies are defined that the later agents reuse.

**03 — the spec comes first.** A written build spec, handed to two different
builders, producing two defensible workflows: Claude took the spec's documented
fallback (schedule + poll), the n8n AI Assistant took its first choice (a native
Jira event trigger) and also built the optional export. Both are here to compare.

**04 — a human in the loop.** A scheduled workflow that pauses on a Telegram
`sendAndWait` and only publishes after approval, with a Merge node to recombine
the waiting branch with the generated image.

The next step after these is
[`08_Automate_Daily_QA_Tasks_AI_Agents`](../08_Automate_Daily_QA_Tasks_AI_Agents),
where the contract, the guard rails and defensive parsing all ship inside a
single workflow.

## Patterns worth carrying

- **Agent-with-tools vs pipeline.** In `01` and `02` the Jira and Sheets nodes
  hang off the agent as tools, so ordering lives in the prompt. In `03` and `04`
  the nodes are wired in sequence, so the canvas guarantees the order. Choose the
  second when the order matters and you do not want to argue with a model about it.
- **Dedupe against the destination.** `03` looks the Jira key up in the sheet
  before spending a model call — what makes a 15-minute poll safe.
- **Never trust the model's JSON.** Parse it in a Code node or with a structured
  output parser; both appear in `03`.
- **Write the fallback into the spec.** `03` names what to do when the preferred
  trigger is unavailable, which is why both builds are correct.
- **A gate has to branch.** `04`'s approval step is a real fork, not a
  notification.

## Common setup

Every workflow is exported **inactive** except where its own README says
otherwise, and each needs its credentials attached after import. Several carry
values from this account that must be changed before a first run — a hardcoded
Google Doc URL in `01`, a placeholder `YOUR_PROJECT_KEY` in the `03` JQL, and a
Telegram chat id and LinkedIn person in `04`. Each folder's README lists its own.
