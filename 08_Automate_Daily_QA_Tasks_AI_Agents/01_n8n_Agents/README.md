# n8n Agents (01–06)

The six agents of [Automate Daily QA Tasks](../) that run in n8n. Each takes an input a tester already has — a
screenshot, CI runs, a load test CSV, an OpenAPI spec — and hands back the write-up they would otherwise do by hand.

| | Agent | Input | What comes back |
|---|---|---|---|
| 01 | [Screenshot to Bug Reporter](01_Screenshot_To_Bug_Reporter_AI_Agent) | A screenshot, optional logs, through a web form | A Jira ticket with symptom, expected vs actual, severity, priority and the screenshot attached |
| 02 | [Flaky Test RCA Analyzer](02_Flaky_Test_RCA_Analyzer) | Several CI runs of one test | What the failures share, posted to Slack |
| 03 | [Performance Test Analyzer](03_Performance_Test_Analyzer) | A JMeter results CSV | A one-page executive summary, sent to Telegram |
| 04 | [Persona-Based Testing Engine](04_Persona_Based_Testing_Engine) | A feature and the people who use it | A separate test flow for each persona, written into Google Sheets as a working test list |
| 05 | [Visual Diff Explainer](05_Visual_Diff_Explainer) | A before and an after screenshot | What changed, in words, commented on the Jira ticket |
| 06 | [Swagger to API Tests](06_Swagger_To_API_Tests) | An OpenAPI spec | A baseline API suite as a Postman collection and a RestAssured JUnit class |

Each folder holds:
- the workflow export (`*_n8n_workflow.json`);
- a sample input to try it with (`sample_*`, agents 02–06);
- screenshots of a real run;
- a `README.md` (how to run it) and a `plan.md` (why it is built that way).

**To run one:** in n8n, **Workflows → Import from File**, pick the JSON, and attach your own credentials to the
nodes that need them (Groq, and Jira, Slack or Telegram where the agent reports). The credential IDs in an export
belong to the original instance and do not resolve on yours. Agent 01 also runs as a live form:
<https://jayamvishnudeep.app.n8n.cloud/form/report-bug>.

Agents 07–15, which write files to disk, are in [`../02_Langflow_Agents`](../02_Langflow_Agents).
