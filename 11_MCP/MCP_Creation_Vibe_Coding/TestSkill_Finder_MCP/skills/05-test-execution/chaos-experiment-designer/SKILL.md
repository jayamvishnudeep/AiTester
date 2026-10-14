---
name: chaos-experiment-designer
description: >-
  Design controlled chaos engineering experiments to test resilience. Use when a team says
  "what happens if the database goes down", "plan a chaos experiment", "test our retries and
  failover", or "game day". Produces experiments with a steady-state hypothesis, the fault to
  inject (instance loss, latency, dependency outage, resource exhaustion), blast radius,
  abort conditions, monitoring and the expected recovery — starting small in test
  environments and run only with the system owners' approval.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Execution
  version: 1.0.0
---

# Chaos Experiment Designer

You test **how the system behaves when something breaks**, in a controlled experiment with a
hypothesis, a small blast radius and a way to stop at once.

## When to use
- The team relies on retries, timeouts, circuit breakers, replicas or failover and has never
  seen them work.
- A game day or resilience review is planned.

## Workflow
1. **Define steady state** — a measurable signal that the system is healthy: success rate,
   p95 latency, orders per minute.
2. **Write the hypothesis** — "If <fault> happens, steady state holds (or recovers within
   <time>) because <mechanism>".
3. **Choose one fault** — kill an instance or container, add latency to a dependency, make a
   dependency return errors, exhaust CPU, memory or disk, drop network between services.
   Tools such as Chaos Mesh, LitmusChaos, AWS Fault Injection Service or toxiproxy, depending
   on the platform.
4. **Limit the blast radius** — one service, a small share of traffic, a test environment
   first; production only when the team is ready and owners approve.
5. **Abort conditions and rollback** — the signal that stops the experiment immediately, and
   how the fault is removed.
6. **Run, observe, record** — what happened against the hypothesis, alerts that fired or did
   not, and the follow-up fixes.

## Output shape
```
## Chaos Experiment — payment-service latency
Steady state: checkout success ≥ 99%, p95 < 800 ms
Hypothesis: with 2 s latency on the fraud-check API, checkout still succeeds within 3 s
            because the client times out at 1 s and uses the fallback rule
Fault: +2 s latency on fraud-check (toxiproxy), staging, 10 minutes
Blast radius: staging only · Abort if checkout success < 95% for 2 minutes
Observed: ... · Alerts fired: ... · Follow-ups: ...
--- APPROVAL --- service owner · on-call engineer
```

## Guardrails
- Never inject faults into production without owner approval, monitoring and an abort plan.
- One fault per experiment, so the result can be explained.
- A failed hypothesis is a success for the experiment; record it and fix the weakness.
