# Bug triage resources

The prompts and the sheet schema behind the [Bug Triage AI Agent](../README.md).

| File | What it is |
|---|---|
| [BugTriage_Prompt.md](BugTriage_Prompt.md) | The first prompt: a persona and triage principles, starting with "severity is technical impact, priority is business urgency". It taught judgement but not behaviour, so the agent described its writes instead of making them |
| [Modified_BugTriage_prompt.md](Modified_BugTriage_prompt.md) | The rewrite the agent runs on: the same judgement as an executable contract, with a mandatory execution order, the connected tools named verbatim, and Jira retrieval rules |
| [Jira_Bug_Triage_Sample.xlsx](Jira_Bug_Triage_Sample.xlsx) | The column schema of the Google Sheet the agent writes. Build your sheet from it before the first run |

The difference between the two prompts is the lesson of the folder; the
[parent README](../README.md#the-prompt-is-the-agent) walks through it.
