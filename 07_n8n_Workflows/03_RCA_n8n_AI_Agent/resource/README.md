# RCA agent spec

[rca-automation-n8n-prompt.md.md](rca-automation-n8n-prompt.md.md) is the specification both versions of the
[Root Cause Analysis AI Agent](../README.md) were built from: detect new production bugs in Jira, generate a
structured root cause analysis for each, and write one row per ticket into a Google Sheet laid out like an Excel
RCA template.

The same spec went to two builders, Claude and the n8n AI Assistant, and both exports sit in the parent folder.
The parent README compares the calls each one made.
