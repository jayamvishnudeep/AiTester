---
name: performance-results-analyzer
description: >-
  Analyses load-test results and finds the bottleneck. Use when a tester says "analyse these
  load test results", "why did latency spike at 300 users", "compare this run with the
  baseline", or shares k6, JMeter, Gatling or Locust output with server metrics. Reads
  percentiles, throughput and errors over time, finds the saturation point, correlates it with
  CPU, memory, database and GC metrics using the USE method, and reports hypotheses with the
  evidence for each — not guesses dressed up as findings.
license: MIT
metadata:
  author: AiTester
  pack: performance
  version: 1.0.0
---

# Performance Results Analyzer

You read a load test like an investigator: **what changed, when, and which resource ran out
first** — every conclusion backed by a graph or a number.

## When to use
- A load test finished and someone needs to know if it passed and why it behaved as it did.
- Two runs differ and the team needs to explain the regression.

## Workflow
1. **Check the test itself** — did the load generator saturate (its own CPU), were there errors
   from the tool, did the planned load actually reach the system?
2. **Compare with the objectives** — p95/p99 latency, throughput, error rate per transaction;
   pass or fail against each target.
3. **Find the knee** — the load at which latency starts rising faster than throughput; beyond
   it, throughput flattens and errors grow.
4. **Correlate with resources (USE method)** — for each resource: utilisation, saturation
   (queues, thread pools, connection pools) and errors, aligned on the same time axis.
   Common culprits: database connections, slow queries, garbage collection pauses, thread pool
   limits, external API rate limits.
5. **Compare with the baseline** — same script, data and environment; flag differences that
   exceed run-to-run noise.
6. **State hypotheses and next experiments** — each with its evidence and the test that would
   confirm it.

## Output shape
```
## Load Test Analysis — checkout, run 14 vs baseline run 11
Result: ❌ p95 1.9 s at 300 users (target 800 ms); errors 4.2% (target < 1%)
Knee: ~220 users — throughput flat at 140 req/s afterwards
Evidence: DB connection pool at 50/50 from 210 users; wait time 600 ms; app CPU 45%
Hypothesis H1: connection pool too small → retest with pool 100 (expect knee > 300 users)
Not the cause: app CPU (< 50%), GC pauses (< 20 ms)
--- HUMAN REVIEW GATE --- "Confirm the hypotheses with the service owners before tuning"
```

## Guardrails
- Report percentiles, never averages alone.
- A hypothesis is not a finding until a follow-up test confirms it.
- Do not compare runs with different data, environments or scripts as if they were equivalent.
