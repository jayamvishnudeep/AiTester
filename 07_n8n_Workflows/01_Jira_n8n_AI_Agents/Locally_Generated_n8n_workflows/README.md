# Locally generated n8n workflow

The local variant of the [Jira AI Agents](../README.md#the-local-variant): the same fetch-a-ticket, write-a-test-plan
shape, rebuilt to use a Groq chat model and to write to Google Sheets instead of Google Docs.

| File | What it is |
|---|---|
| [Locally_n8n_Fetch Jira and Create Test Plan.json](Locally_n8n_Fetch%20Jira%20and%20Create%20Test%20Plan.json) | The workflow export. Import it with **Workflows → Import from File** |
| [Fetch jira ticket and create a test plan.png](Fetch%20jira%20ticket%20and%20create%20a%20test%20plan.png) | The workflow on the n8n canvas |

After importing, attach your own Jira, Groq and Google Sheets credentials; the IDs in the export belong to the
original instance.
