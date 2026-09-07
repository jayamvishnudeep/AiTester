# Automate Daily QA Tasks with AI Agents

Agents that take over a job a tester actually does by hand every day. Where
[`07_n8n_Workflows`](../07_n8n_Workflows) was about learning the tool, this
section is about shipping something a colleague could use without being told how
it works.

| | Agent | What it replaces |
|---|---|---|
| 01 | [Screenshot to Bug Reporter](01_Screenshot_To_Bug_Reporter_AI_Agent) | Writing up a bug from a screenshot by hand |

## 01 — Screenshot to Bug Reporter

A tester uploads a screenshot, optionally pastes the logs, and a Jira ticket
comes back with the symptom, the visual detail, expected versus actual,
severity, priority and category already written — with the screenshot attached.

Live form: <https://jayamvishnudeep.app.n8n.cloud/form/report-bug>

It is the first thing in this repo built for someone **other than its author**,
and that changes what mattered: a form and a result page a tester will trust,
guard rails so the output is never confidently wrong, and defensive parsing so a
bad model response cannot reach Jira.

See its [README](01_Screenshot_To_Bug_Reporter_AI_Agent) for the full walkthrough
and screenshots.

## What this section adds over 07

**The contract ships inside the workflow.** No instructions typed into a chat
box. The prompt, the taxonomies and the refusal rules all live in the exported
JSON, so importing it is enough.

**Guard rails, not just prompts.** A screenshot cannot show how someone got
there, so steps to reproduce are never invented — the field reads
`Not Provided - tester to complete` and confidence drops to Low. This is the
`01_LLM_Basics` anti-hallucination rule enforced at the point it would actually
do damage.

**Defensive parsing.** The model returns JSON as a string; it is parsed,
validated against a schema and every missing field defaulted before anything
reaches Jira. A malformed response is treated as a normal case, not an
exception.

**A UI a tester sees.** A styled upload form and a custom confirmation page
served through the Form Ending, rather than n8n's default success screen — with
the ticket key, a link straight to the issue, and an honest list of what the
model could not determine.

## Things learned here worth reusing

- **Binary data does not survive a Code or HTTP node in n8n.** Whatever file
  entered the workflow is gone by the time a later node wants it. Read it back
  off the trigger and re-emit it.
- **Check the rate limit that actually binds.** Groq's free tier runs out of
  output tokens per minute long before it runs out of requests per day, and it
  counts the ceiling you request rather than what you use.
- **Turn reasoning off on a thinking model when you want JSON.** Left on, the
  whole completion budget goes to reasoning and the JSON comes back truncated.
- **Read the tool's own source before styling it.** n8n's form template reads a
  CSS variable it never defines, and guessing at selectors matched the wrong
  elements.
