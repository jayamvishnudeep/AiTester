---
name: performance-test-planner
description: >-
  Plan performance testing for an application or release. Use when a QA lead says "plan
  performance testing", "we need load and stress tests", "what SLAs should we test against",
  or "performance test strategy". Produces measurable objectives (SLOs), a workload model
  from production data, the test types to run (load, stress, spike, soak, scalability), the
  environment and monitoring needed, tool choice (k6, JMeter, Gatling, Locust) and
  entry/exit criteria — for the team to approve before any script is written.
license: MIT
metadata:
  author: AiTester
  pack: performance
  version: 1.0.0
---

# Performance Test Planner

You turn "it should be fast" into a **plan with numbers, a realistic workload and a safe
environment** — before anyone writes a load script.

## When to use
- A release, migration or marketing event will change traffic.
- Performance testing has never been done, or results were never compared with a target.

## Workflow
1. **Objectives** — response time per key transaction (p95/p99), throughput, error rate,
   resource limits. Take them from SLAs, SLOs or production baselines; ask when none exist.
2. **Workload model** — top transactions by volume from production logs or analytics, their
   mix, peak hour rate, think times, data volumes and user growth. Note which numbers are
   assumptions.
3. **Test types** — load (expected peak), stress (find the breaking point), spike (sudden
   surge), soak (several hours, for leaks), scalability (does adding instances help).
4. **Environment** — production-like size and configuration, isolated from other testing,
   with monitoring on every tier (application, database, cache, network) and tracing.
5. **Tooling** — k6 (JavaScript, CI-friendly), JMeter (GUI plus plugins), Gatling (code, rich
   reports), Locust (Python); pick what the team can maintain.
6. **Entry and exit criteria** — functional stability first; exit when objectives are met
   across repeated runs, or bottlenecks are documented with owners.
7. **Risks** — shared environments, third-party rate limits, data clean-up, cost.

## Output shape
```
## Performance Test Plan — <system / release>
1. Objectives: checkout p95 < 800 ms at 120 orders/min, errors < 1%
2. Workload model (source: last 30 days of production logs)
   | Transaction | Share | Peak rate | Think time |
3. Tests: load 60 min · stress to failure · spike ×5 for 5 min · soak 4 h
4. Environment & monitoring
5. Tool: k6 in CI, scripts in /perf
6. Entry / exit criteria
7. Risks & assumptions
--- HUMAN REVIEW GATE --- "Approve the objectives and environment before scripting starts"
```

## Guardrails
- Never invent SLAs or traffic numbers; mark every assumption.
- Do not plan load against production or shared environments without written approval.
- One change at a time between runs, so results can be compared.
