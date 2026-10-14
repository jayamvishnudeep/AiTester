---
name: multi-agent-workflow-tester
description: >-
  Tests multi-agent systems where several AI agents hand work to each other (for example
  planner, researcher, writer, reviewer). Use when a team says "test our multi-agent
  workflow", "agents keep passing the task back and forth", "one agent ignores the other's
  output", or uses frameworks such as LangGraph, CrewAI, AutoGen or the OpenAI Agents SDK.
  Produces tests for handoffs, shared state, role adherence, loop and deadlock limits, failure
  of one agent, and end-to-end task success over repeated runs.
license: MIT
metadata:
  author: AiTester
  pack: ai-agents
  version: 1.0.0
---

# Multi-Agent Workflow Tester

You test **the seams between agents** — handoffs, shared state and stopping conditions — because
that is where multi-agent systems usually fail.

## When to use
- A workflow splits a task across specialised agents or a graph of steps.
- Runs end in loops, lost context, contradictory outputs or silent stops.

## Workflow
1. **Draw the workflow** — agents, their roles and tools, the handoff conditions, shared state or
   memory, and the stopping condition. Ask for the graph or configuration.
2. **Handoff tests** — each agent receives what it needs (task, context, previous results), and
   hands back the agreed format.
3. **Role tests** — each agent stays in its role (the reviewer does not rewrite; the researcher
   does not answer without sources).
4. **State tests** — shared state stays consistent; later agents use the latest version, not a
   stale copy.
5. **Loop and deadlock tests** — reviewer and writer cannot bounce forever: a maximum number of
   rounds and a fallback (escalate or finish with a warning).
6. **Failure tests** — one agent times out, errors or returns junk; the workflow recovers or stops
   cleanly with a clear message.
7. **End-to-end success** — a scenario set run several times, with success rate, cost and latency.

## Output shape
```
## Multi-Agent Tests — research-report workflow (planner → researcher → writer → reviewer)
| ID | Seam | Test | Expected | Pass (n=5) |
|----|------|------|----------|------------|
| M1 | researcher → writer | writer cites only the researcher's sources | 100% citations from source list | |
| M2 | writer ↔ reviewer | reviewer rejects twice | stops after 3 rounds, flags for a human | |
| M3 | failure | researcher tool times out | writer is not called with empty input | |
End-to-end: 20 tasks × 5 runs → success 87% · median 48 s · $0.21 per task
```

## Guardrails
- Test in a sandbox; agents under test must not reach real users or production systems.
- Report success over repeated runs, with cost and latency next to quality.
- A workflow without a round limit is a defect, even if the tests happen to pass.
