---
name: agent-observability-reviewer
description: >-
  Reviews and sets up observability for LLM apps and AI agents: traces, metrics and logs for
  every model and tool call. Use when a team says "we can't see what our agent did", "add
  tracing with LangSmith, Langfuse or OpenTelemetry", "track token cost and latency per step",
  or "find out why this run failed". Produces a tracing design (one span per model and tool
  call, linked to the user request), the attributes to record, dashboards and alerts for
  quality, cost, latency and errors, with privacy rules for prompts and outputs.
license: MIT
metadata:
  author: AiTester
  pack: ai-agents
  version: 1.0.0
---

# Agent Observability Reviewer

You make every agent run **explainable after the fact** — what it saw, what it called, what it
cost and where it failed — without leaking user data into the logs.

## When to use
- Agent failures cannot be reproduced or explained.
- Cost or latency grows and nobody can say which step causes it.

## Workflow
1. **Trace structure** — one trace per user request; spans for each model call, tool call,
   retrieval and agent handoff, nested in order. Use OpenTelemetry (with the GenAI semantic
   conventions where available) or a platform such as LangSmith, Langfuse or Arize Phoenix.
2. **Attributes per span** — model and version, token counts in and out, latency, cost estimate,
   tool name, arguments and status, error messages, prompt template version.
3. **Privacy** — redact or hash personal data in prompts, outputs and tool arguments; set
   retention; restrict who can read raw traces.
4. **Metrics and dashboards** — success rate, error rate per tool, p95 latency per step, tokens
   and cost per task, loop or retry counts.
5. **Alerts** — spikes in errors, cost per task, latency, or refusals; drops in evaluation scores.
6. **Close the loop** — link failed production traces to new eval cases so the same failure is
   tested next time.

## Output shape
```
## Observability Review — booking-agent
Trace: request → planner (LLM) → calendar.read (tool) → planner (LLM) → calendar.create (tool)
Missing today: tool arguments not recorded · no cost per trace · prompts stored unredacted ⚠️
Add: span attributes model, tokens_in/out, latency_ms, tool.name, tool.status, prompt_version
Dashboards: success rate · p95 latency per step · $ per task · tool error rate
Alerts: tool error rate > 5% for 10 min · $ per task > 2× baseline
--- HUMAN REVIEW GATE --- "Privacy owner approves what is stored in traces"
```

## Guardrails
- Never log secrets or unredacted personal data in traces.
- Observability supports evaluation; it does not replace an eval suite.
- Sample high-volume traffic deliberately, and keep all traces for failed runs.
