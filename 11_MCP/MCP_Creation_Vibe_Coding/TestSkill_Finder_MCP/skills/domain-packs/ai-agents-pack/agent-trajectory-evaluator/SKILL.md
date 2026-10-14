---
name: agent-trajectory-evaluator
description: >-
  Evaluates an AI agent's trajectory — the sequence of reasoning steps and tool calls it took
  — against expected behaviour. Use when a team says "check the steps our agent took", "did
  the agent call the right tools in the right order", "why did the agent loop", or shares
  agent traces. Compares actual and reference trajectories with exact, in-order, any-order or
  subset matching, checks arguments, flags loops, redundant and forbidden calls, and scores
  step efficiency alongside the final answer.
license: MIT
metadata:
  author: AiTester
  pack: ai-agents
  version: 1.0.0
---

# Agent Trajectory Evaluator

You judge **how the agent got there, not only where it ended** — a right answer reached through
a forbidden or wasteful path is still a defect.

## When to use
- The final answer looks right but the agent is slow, costly or takes risky steps.
- Traces exist (LangSmith, Langfuse, OpenTelemetry, framework logs) and need systematic checks.

## Workflow
1. **Get the traces** — for each run: the ordered tool calls with arguments and results, the
   model's messages, and the final answer.
2. **Write the reference per scenario** — the required tools, the forbidden tools, and whether
   order matters.
3. **Pick a match mode per scenario:**
   - Exact: the same calls in the same order (strict workflows).
   - In order: required calls appear in order, extra calls allowed.
   - Any order: required calls appear in any order.
   - Subset: no call outside an allowed set.
4. **Check arguments** — required fields present, values derived from the user request or earlier
   tool results, not invented.
5. **Flag bad patterns** — repeated identical calls (loops), calls after the task was done,
   forbidden or destructive calls without confirmation, ignored tool errors.
6. **Score** — trajectory match, step count against the reference, final answer correctness;
   aggregate over repeated runs.

## Output shape
```
## Trajectory Check — "refund order 4411" (run 3 of 5)
Reference (in order): orders.get(4411) → refunds.create(order=4411) ; forbidden: email.send before refund
Actual: orders.get(4411) → orders.get(4411) → refunds.create(order=4411, amount=25.00) → email.send
Match: in-order ✅ · Loop: orders.get repeated ⚠️ · Arguments: amount taken from order total ✅
Steps: 4 vs reference 2 · Final answer: correct
Suite (40 scenarios × 5 runs): trajectory pass 92% · loops in 6% of runs
```

## Guardrails
- Expected trajectories come from the workflow design, not from what the agent happened to do.
- Do not penalise harmless extra steps in "in order" mode; do penalise forbidden ones always.
- Mask personal data in traces before sharing them.
