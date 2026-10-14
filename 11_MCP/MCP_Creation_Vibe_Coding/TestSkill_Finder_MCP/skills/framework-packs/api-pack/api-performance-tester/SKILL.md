---
name: api-performance-tester
description: >-
  Plans and scripts API load tests with k6. Use when a team says "load test this API", "can
  the service handle 500 users", "write a k6 script", "set performance thresholds", or needs
  load, stress, spike or soak tests for an API. Produces a workload model from real traffic or
  agreed targets, a k6 script with scenarios, checks and thresholds (p95 latency, error rate),
  and a results template — run only against environments sized and approved for load.
license: MIT
metadata:
  author: AiTester
  pack: api
  version: 1.0.0
---

# API Performance Tester

You turn "is it fast enough?" into **measurable thresholds and a repeatable k6 test**, against
an environment where load is allowed.

## When to use
- A release adds traffic or a new endpoint, or an SLA has to be proven.
- Someone asks about load, stress, spike or soak behaviour of an API.

## Workflow
1. **Agree the targets** — requests per second or virtual users, p95/p99 latency, error rate,
   duration. Take them from SLAs or production metrics; if none exist, ask. Never invent them.
2. **Model the workload** — which endpoints in which mix, think time, test data volume.
3. **Choose the test type** — load (expected peak), stress (beyond peak until it breaks), spike
   (a sudden jump), soak (hours at normal load to find leaks).
4. **Script it in k6** — `options.scenarios` (for example `ramping-vus` or
   `constant-arrival-rate`), `check()` on responses, and `thresholds` that fail the run.
5. **Environment** — production-like size, monitoring on (CPU, memory, database), data reset
   between runs, and written approval to generate load.
6. **Report** — thresholds passed or failed, latency percentiles, errors, the bottleneck found.

## Output shape
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    peak: {
      executor: 'ramping-vus',
      stages: [
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '1m', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],   // fewer than 1% errors
    http_req_duration: ['p(95)<500'], // 95% of requests under 500 ms
  },
};

export default function () {
  const res = http.get(`${__ENV.BASE_URL}/api/orders?limit=20`);
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
```

## Guardrails
- Never load-test production or shared environments without written approval.
- Thresholds come from agreed targets; an invented threshold makes a meaningless pass.
- Report percentiles, never averages alone.
