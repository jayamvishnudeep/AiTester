# Langflow

Three agents built in Langflow, in the order they were built. Each folder has
its own README with the detail; this page is the map and the through-line.

| | Folder | What it does | Shape |
|---|---|---|---|
| 01 | [Bug Triage — static](01_Bug%20Triage%20Static%20%28Without%20Chat%20Trigger%29) | Fetch a Jira ticket and return severity, priority and review comments | Pipeline, no chat box |
| 02 | [Bug Triage AI Agent](02_Bug%20Triage%20AI%20Agent) | The same triage, driven by a chat box, with a browser UI on top | Chat → agent → Jira |
| 03 | [Flaky Test Case Finder](03_Flaky_Test_case_Finder) | Compare two Playwright runs and name the flaky tests | Custom component + LLM |

## The through-line

Read in order, these three are one story about **moving work out of the model
and into code**.

**01 — the flow is the contract.** No chat trigger: the flow fetches the ticket
itself from a ticket key, so it runs identically from the Playground, from
Postman, or from a scheduled call. Everything the model needs to know is in the
prompt inside the exported JSON, not typed in at run time.

**02 — the same agent, made usable.** The chat trigger comes back, an agent
decides when to call the Jira tool, and a small browser UI sits in front so
someone who has never opened Langflow can still triage a ticket. The Postman
collection is the same flow called as an API.

**03 — the model stops counting.** Whether a test is flaky is a comparison
between two runs, and comparisons are something code does exactly and a model
does approximately. `flaky_comparator.py` is a custom component that does the
comparing; the model only writes the summary. It also draws the distinction that
matters: a test failing in **both** runs is not flaky, it is broken, and the two
are reported separately so nobody spends a morning re-running a real defect.

The next step after these is
[`08_Automate_Daily_QA_Tasks_AI_Agents/02_Langflow_Agents`](../08_Automate_Daily_QA_Tasks_AI_Agents/02_Langflow_Agents),
where that split — code computes the facts, the model writes the prose — becomes
the house pattern for every agent from 07 onward.

## Patterns worth carrying

- **A flow with no chat box is reproducible.** 01 runs the same way from the
  Playground, Postman or cron, because nothing it needs arrives by hand.
- **Put the counting in a custom component.** 03's comparator is plain Python,
  so the numbers are exact and repeatable, and the token budget is spent on the
  explanation rather than on the data.
- **Name the thing that is not the thing.** "Failed twice" is not flake. An
  agent that does not separate them produces a list nobody trusts twice.
- **A `.postman_collection.json` beside the flow is worth keeping.** It is the
  cheapest proof that the flow works as an API and not only in the Playground.

## Common setup

Every flow here needs the same two things after import:

1. **Langflow running**, normally at `http://127.0.0.1:7860`.
2. **Credentials as global variables**, never literals in the JSON — Settings →
   Global Variables. The Groq key is stored as `GROQ_API_KEY`, type
   **Credential**; the Jira flows also need their Jira URL, email and API token.

The Jira flows carry a project key and ticket keys from this account, so change
those before a first run. `03` reads its two Playwright reports from a folder
path that is absolute on the machine it was built on — point it at the included
`results/` folder, or at your own.

`langflow.log` and `langflow-error.log` are runtime output and are gitignored;
they are rewritten on every run and are not worth reading a year from now.
