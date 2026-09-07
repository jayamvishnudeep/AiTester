# Jira AI Agents — n8n

The first n8n agents in this repo. Three variations on one shape: read a Jira
ticket, have a model turn it into something useful, write the result into a
Google Doc.

This is where the agent pattern was learned, and it is worth reading in that
spirit — the later agents in `02_`, `03_` and `08_` are all refinements of what
is here.

## One shape, three outputs

Every workflow in this folder is the same six nodes:

```
When chat message received (chatTrigger)
  -> AI Agent
       ├── Brain           (gpt-5-mini)
       ├── Simple Memory   (buffer window)
       ├── Jira tool       (get one issue)
       └── Google Docs     (update: insert the agent's output)
```

Only the last node and the request change.

### 1. Fetch the ticket

![The fetch workflow on the n8n canvas](n8n_workflow_screenshots/Fetch%20Jira%20ticket%20and%20append%20the%20output%20to%20Google%20Docs.png)

`Fetch JIRA Ticket using n8n and append output to Google Docs.json` — the
starting point. Pull one issue and write it into a document. No transformation,
which makes it the right first thing to build: it proves the Jira credential,
the tool call and the Docs write before any of the thinking is added.

### 2. Create a test plan

![The test plan workflow on the n8n canvas](n8n_workflow_screenshots/Created%20Test%20Plan%20from%20JIRA%20Ticket%20and%20the%20output%20is%20given%20to%20Google%20Docs.png)

`Create Test Plan From Jira Ticket and append output to Google Docs.json` —
same six nodes, but now the model turns the ticket into a test plan before the
document is written.

### 3. Create a test strategy

![The test strategy workflow on the n8n canvas](n8n_workflow_screenshots/Create%20Test%20Strategy.png)

`Create Test Strategy from Jira ticket and append output to Google Docs.json` —
identical again, aimed at a strategy rather than a plan. Proof that once the
shape works, a new deliverable costs one node change and a different request.

## The local variant

![The locally generated workflow, using a Groq chat model and writing to Google Sheets](Locally_Generated_n8n_workflows/Fetch%20jira%20ticket%20and%20create%20a%20test%20plan.png)

`Locally_Generated_n8n_workflows/Locally_n8n_Fetch Jira and Create Test Plan.json`
— the same shape rebuilt with two swaps:

| | Cloud versions | Local version |
|---|---|---|
| Model | OpenAI `gpt-5-mini` | **Groq** (`lmChatGroq`) |
| Output | Google Docs, `update` | **Google Sheets**, `appendOrUpdate` |

Worth noting because Groq is the provider the Screenshot to Bug Reporter in
`08_` ends up using for vision — this folder is where it first appears, and the
reason is the same both times: it is free.

## The thing these get wrong

**The AI Agent nodes have no system message.** Open any of them and the
parameters are literally `{"options":{}}`. Every instruction — be a QA
engineer, produce a test plan, use this format — was typed into the chat box at
run time and is not saved anywhere in the export.

That is why these workflows cannot be handed to someone else and re-run to the
same result, and it is the exact problem the `02_BugTriage` prompt rewrite
solves by moving the whole contract into the agent. If you are revising the
progression in this repo, that is the single biggest step:

> **`01_` — the shape works, the prompt lives in the chat.**
> **`02_` — the prompt becomes a written contract, and the agent becomes repeatable.**
> **`03_` — a spec is written first, and two different builders implement it.**
> **`08_` — the contract, the guard rails and the defensive parsing all ship inside the workflow.**

The Google Docs nodes also carry a **hardcoded document URL**, so an import
writes into the document from this account until it is changed.

## Setting it up

Import a workflow, then attach three credentials: OpenAI (or Groq for the local
variant), Jira Software Cloud, and Google Docs (or Sheets). Then change the
document URL on the output node to one of your own.

Start it from the chat panel, and remember that the instruction goes in the chat
message — the agent has none stored.

All four are exported inactive.
