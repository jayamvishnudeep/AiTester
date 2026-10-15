# Langflow Agents (07–15)

The nine agents of [Automate Daily QA Tasks](../) that run in Langflow. Each one ends by writing a file to disk — a
spec, a Page Object, a report — which is why they run on your own machine rather than in n8n Cloud.

| | Agent | Reads | Writes |
|---|---|---|---|
| 07 | [Manual to Playwright Tests](07_Manual_To_Playwright_Tests_AI_Agent) | Written manual test cases | Playwright test files in TypeScript |
| 08 | [Page Object Generator](08_Page_Object_Generator_AI_Agent) | An HTML snapshot | A Playwright Page Object class in TypeScript |
| 09 | [Framework Auditor](09_Framework_Auditor_AI_Agent) | An automation repository | An audit of its anti-patterns and out-of-date dependencies |
| 10 | [Vendor License Monitor](10_Vendor_License_Monitor_AI_Agent) | A tool login activity export | Which paid seats nobody uses |
| 11 | [CI/CD Failure Analyzer](11_CI_CD_Failure_Analyzer_AI_Agent) | A Jenkins, GitHub Actions or CircleCI log | A root cause analysis of the failure |
| 12 | [Self-Healing Selectors](12_Self_Healing_Selectors_AI_Agent) | Selectors that stopped finding their elements | Replacements, each run against the page and confirmed to match exactly one element |
| 13 | [Smart Regression Advisor](13_Smart_Regression_Advisor_AI_Agent) | A git diff | The tests that can reach the changed code, as a regression plan |
| 14 | [Meeting Transcript to Requirements](14_Meeting_Transcript_To_Requirements_AI_Agent) | A Zoom or Teams transcript | Jira-ready requirements from what was agreed |
| 15 | [Security Test Generator](15_Security_Test_Generator_AI_Agent) | An API spec | The OWASP injection and access-control checks worth running |

Each folder holds:
- the flow export (`*_langflow_flow.json`);
- the Python components that do the counting and comparing, readable on their own, with a test file
  (`test_*.py`) that runs with no Langflow and no network;
- sample input, and the output the flow generated (`generated/` for 07–08, `reports/` for 09–15);
- screenshots of a Playground run;
- a `README.md` (how to run it) and a `plan.md` (why it is built that way).

**To run one:**
1. Start Langflow (see [09_LangFlow](../../09_LangFlow)).
2. Add a global variable named exactly `GROQ_API_KEY`, of type **Credential**.
3. Import the flow JSON.
4. Repoint the path fields its README lists.

The quickest check is the component test:

```bash
cd 09_Framework_Auditor_AI_Agent
../../../09_LangFlow/.venv/Scripts/python.exe test_framework_auditor.py
```

Agents 01–06 are in [`../01_n8n_Agents`](../01_n8n_Agents).
