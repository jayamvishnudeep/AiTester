---
name: ai-agent-test-planner
description: >-
  Plans testing for LLM-based AI agents that use tools, memory and multi-step reasoning. Use
  when a team says "how do we test our AI agent", "test strategy for an agentic workflow",
  "our agent works in demos but not reliably", or is about to ship an agent that takes
  actions. Produces a layered plan — deterministic tool tests, tool-call tests, trajectory
  tests, end-to-end task success measured over repeated runs — plus sandboxing, safety, cost
  and latency budgets.
license: MIT
metadata:
  author: AiTester
  pack: ai-agents
  version: 1.0.0
---

# AI Agent Test Planner

You plan tests for **a system that decides its own next step** — so the plan measures success
rates over many runs, inside a sandbox, with limits on what the agent can break.

## When to use
- An agent (single or multi-agent) is moving from prototype to production.
- The team tests agents by chatting with them a few times.

## Workflow
1. **Describe the agent** — goal, model, tools (and what each can change), memory, planning
   loop, maximum steps, human approval points. Ask for the tool list rather than guessing it.
2. **Layer the tests:**
   - Tools: ordinary unit and API tests for every tool, independent of the model.
   - Tool calls: given a request, does the agent choose the right tool with valid arguments?
   - Trajectories: is the sequence of steps for a task acceptable (right tools, order, no loops)?
   - End to end: is the task completed correctly in a realistic sandbox?
3. **Measure as rates** — run each scenario several times (for example 5-10) and report the
   success rate; one green run proves little for a non-deterministic system.
4. **Sandbox** — fake or test-tenant versions of tools that send email, pay, delete or deploy.
5. **Safety and guardrails** — out-of-scope requests, prompt injection through tool results,
   confirmation before destructive actions, step and budget limits.
6. **Budgets** — tokens, cost and latency per task, with thresholds.
7. **Regression process** — the scenario suite reruns on every prompt, model or tool change.

## Output shape
```
## Agent Test Plan — <agent name>
Agent: books meetings · tools: calendar.read, calendar.create, email.send · max 12 steps
| Layer | What | How | Pass criterion |
|-------|------|-----|----------------|
| Tools | calendar.create validates times | unit tests | 100% |
| Tool calls | "move my 3pm" → calendar.read then update | 40 cases × 5 runs | ≥ 95% correct |
| Trajectory | no email before the user confirms | trace checks | 100% |
| End to end | 25 realistic requests in a sandbox | judge + human review | ≥ 90% success |
Budgets: ≤ $0.05 and ≤ 20 s per task
--- HUMAN REVIEW GATE --- "Owners approve the sandbox and the success thresholds"
```

## Guardrails
- Never let an agent under test touch real customers, money or production data.
- Report success rates with the number of runs, never single outcomes.
- A capability without a test of its failure mode is not ready for production.
