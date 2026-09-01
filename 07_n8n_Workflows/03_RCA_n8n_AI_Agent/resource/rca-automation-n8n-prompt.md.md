# Prompt: Build an Automated Production Bug RCA Workflow in n8n

Build an n8n workflow that automatically detects new production bugs in Jira, generates a structured Root Cause Analysis (RCA) using an AI Agent, and writes the RCA into a shared Google Sheet (styled to mirror an Excel RCA template) — with one new row appended per bug ticket.

## Trigger

Use a **Jira Trigger** node configured to fire on new issue creation and issue updates, filtered to only match production bugs via JQL. Use this JQL (adjust project key as needed):

```
project = "YOUR_PROJECT_KEY" AND issuetype = Bug AND (environment ~ "Production" OR labels = "production" OR priority in (Highest, High)) AND status != Done
```

If a native event-based Jira Trigger isn't available for this Jira instance/plan, fall back to:
- A **Schedule Trigger** (every 5–15 minutes)
- Followed by a **Jira — Get Many Issues** node using the same JQL
- Followed by a **Filter/IF** node comparing each issue's key against a "already processed" list (see Deduplication below), so the same bug isn't RCA'd twice

## Deduplication

Before generating an RCA, check whether the ticket's Jira key already exists as a row in the target Google Sheet:
- Use a **Google Sheets — Lookup Row** (or equivalent) node matching on `jira_key`
- If found, skip RCA generation (or update only if the ticket status changed to Resolved/Closed, in which case refresh the RCA with final details)
- If not found, proceed to RCA generation

## Data to Extract from Jira

For each matched issue, retrieve:
- Jira key, URL, project, summary, description
- Issue type, status, priority, severity (if custom field exists)
- Reporter, assignee
- Created date, updated date, resolved date (if available)
- Environment, affected version, fix version
- Labels, components
- Steps to reproduce, expected result, actual result (from description or custom fields)
- Comments (for additional context on investigation/fix)
- Linked issues (for regression/duplicate context)
- Resolution field (if already resolved)

Never invent data not present in the Jira issue. If a field is unavailable, use `Not Provided`.

## AI Agent — RCA Generation

Use an **AI Agent** node (Chat Model + this system message) to generate the RCA content from the extracted Jira data:

```
You are a senior QA engineer and Root Cause Analysis specialist. Given the details of a
single production Jira bug ticket, produce a structured Root Cause Analysis.

Use ONLY the information provided in the ticket data. Never invent facts, logs, dates, or
outcomes that are not present in the input. If information needed for a field is missing,
write "Not Provided" for that field rather than guessing.

Produce the following fields exactly, matching this structure:

1. TICKET REFERENCE
   - jira_key, jira_url, summary, reporter, assignee, severity_priority, environment

2. PROBLEM STATEMENT
   - what_happened: a clear, factual description of the observed issue (2-4 sentences)
   - impact_blast_radius: who/what was affected
   - business_impact: revenue, compliance, customer trust, SLA implications if evident from the ticket

3. TIMELINE
   - date_introduced: only if evidence in the ticket suggests when the root cause was introduced (e.g. a mentioned deploy/release); otherwise "Not Provided"
   - date_detected: created date of the ticket, or date mentioned as first noticed
   - date_resolved: resolution date if the ticket is closed/resolved, else "Not Resolved Yet"
   - detection_method: how it was found (customer report, automated test, monitoring, manual QA), based on ticket content

4. ROOT CAUSE ANALYSIS (5 WHYS)
   - why_1 through why_5: a logical chain of "why did this happen" reasoning based on the
     ticket's description, steps to reproduce, and comments. If the ticket does not contain
     enough evidence to complete all 5 levels, stop at the deepest level the evidence supports
     and note in why_5 (or the last completed level) that further investigation is needed.

5. CONTRIBUTING FACTORS
   - technical_factors: any technical conditions mentioned (e.g. missing validation, config drift, race condition)
   - process_factors: any process gaps evident from the ticket (e.g. missing test coverage, no code review mentioned)

6. DETECTION GAP
   - detection_gap: why this wasn't caught before reaching production, if inferable from the ticket

7. CORRECTIVE ACTIONS
   - fix_description: what was done or is planned to resolve the issue, from resolution/comments
   - fix_verification: how the fix was or will be verified, if mentioned

8. PREVENTIVE ACTIONS
   - process_improvement: a reasonable suggested long-term preventive action based on the root cause (e.g. "Add regression test for X", "Add monitoring alert for Y") — this may be a reasonable inference, but must be clearly grounded in the root cause identified, not generic boilerplate
   - suggested_owner: leave as "Not Provided" unless the ticket assigns a specific team
   - suggested_target_date: leave as "Not Provided" unless the ticket specifies one

9. METADATA
   - confidence: High / Medium / Low, based on how much of the above required inference vs.
     direct evidence from the ticket
   - missing_information: semicolon-separated list of what would improve this RCA if available
   - rca_generated_date: today's date in ISO 8601 format

Return ONLY valid JSON with these exact field names (flatten nested sections into individual
keys, e.g. "why_1", "why_2", "technical_factors", "process_factors", etc.) — no markdown, no
commentary, no code fences.
```

## Write to Google Sheets

Use a **Google Sheets — Append or Update Row** node:
- Target: a single shared spreadsheet/tab named `Production Bug RCAs`
- Matching column: `jira_key`
- If `jira_key` exists, update the row (useful for refreshing the RCA once the ticket is resolved with more complete data)
- If not, append a new row

Map these exact columns (matching the RCA template structure):

```
jira_key, jira_url, summary, reporter, assignee, severity_priority, environment,
what_happened, impact_blast_radius, business_impact,
date_introduced, date_detected, date_resolved, detection_method,
why_1, why_2, why_3, why_4, why_5,
technical_factors, process_factors,
detection_gap,
fix_description, fix_verification,
process_improvement, suggested_owner, suggested_target_date,
confidence, missing_information, rca_generated_date
```

Formatting rules for the sheet-write step:
- Send all columns on every write (append or update), even when a value is "Not Provided"
- No line breaks or Markdown inside any cell value
- Keep long text fields concise enough to read in a spreadsheet cell
- Use ISO 8601 for all dates

## Styling the Sheet to Mirror the Excel Template

Since this lives in Google Sheets but should visually mirror the Excel RCA template:
- Freeze the header row
- Bold, colored header row matching the template's blue header style
- Column widths wide enough for `what_happened`, the five `why_` fields, and the corrective/preventive action fields
- Optionally add conditional formatting on the `confidence` column (red = Low, yellow = Medium, green = High) so low-confidence RCAs are easy to spot for manual review

## Optional: Export as .xlsx

Add a final branch (can run on a separate daily/weekly Schedule Trigger, not per-bug) that:
1. Uses a **Google Drive** node's "Download" operation on the spreadsheet, with export format set to `.xlsx`
2. Saves or emails the exported file to a specified location/recipient, so a standing Excel copy is always available alongside the live Google Sheet

## Error Handling

- If the Jira fetch fails, log the error and stop that execution without writing incomplete data
- If the AI Agent returns malformed JSON, retry once; if it fails again, write a row with `confidence = Low` and `missing_information = "AI generation failed — manual RCA needed"`, using whatever raw Jira fields were successfully extracted
- If the Google Sheets write fails, retry once, then log the failed `jira_key` for manual follow-up — do not stop the whole workflow

## Build Order

1. Set up Jira Trigger (or Schedule + Jira search) with the production-bug JQL
2. Add deduplication check against the target Google Sheet
3. Extract and normalize Jira fields
4. Add the AI Agent node with the RCA system message above
5. Parse the AI Agent's JSON output
6. Add the Google Sheets Append/Update node with the exact column mapping
7. Apply header styling/conditional formatting to the sheet (one-time manual setup or via Google Sheets API calls in the workflow)
8. Add error handling branches at each step
9. Add the optional scheduled .xlsx export branch
10. Test end-to-end with a real or sample production bug ticket before activating
