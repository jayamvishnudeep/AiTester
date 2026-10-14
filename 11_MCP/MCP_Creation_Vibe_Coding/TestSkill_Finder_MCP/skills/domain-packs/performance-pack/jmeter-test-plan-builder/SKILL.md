---
name: jmeter-test-plan-builder
description: >-
  Builds Apache JMeter test plans for load testing web apps and APIs. Use when a tester says
  "create a JMeter script", "load test this flow with JMeter", "parameterise users from a CSV",
  "correlate the session token", or "run JMeter in CI". Produces the plan structure (thread
  groups, HTTP samplers, CSV Data Set Config, extractors for correlation, assertions, timers),
  and the non-GUI command with an HTML dashboard report.
license: MIT
metadata:
  author: AiTester
  pack: performance
  version: 1.0.0
---

# JMeter Test Plan Builder

You build **JMeter plans that model real users and run headless in CI** — parameterised data,
correlated tokens, assertions on every sampler.

## When to use
- The team uses JMeter, or needs a GUI-built plan that non-programmers can maintain.
- A flow needs session handling (login tokens, CSRF tokens) under load.

## Workflow
1. **Record or define the flow** — record with the HTTP(S) Test Script Recorder, then remove
   static assets and third-party calls that are not under test.
2. **Thread Group** — users, ramp-up and duration from the workload model (not guesses).
3. **Parameterise** — CSV Data Set Config for credentials and test data; User Defined
   Variables for host, port and protocol.
4. **Correlate** — JSON Extractor or Regular Expression Extractor for tokens and ids, used in
   later requests as `${token}`.
5. **Assertions** — Response Assertion or JSON Assertion on each important sampler, so errors
   count as failures instead of fast "successes".
6. **Think time** — Uniform or Gaussian Random Timer between steps.
7. **Run headless** — `jmeter -n -t plan.jmx -l results.jtl -e -o report/`; disable heavy
   listeners such as View Results Tree during load.

## Output shape
```
## JMeter Plan — checkout.jmx
Test Plan
├── User Defined Variables: HOST, PROTOCOL
├── CSV Data Set Config: users.csv → USERNAME, PASSWORD
└── Thread Group: 100 users · ramp-up 300 s · duration 1800 s
    ├── HTTP Request: POST /api/login
    │   └── JSON Extractor: token ← $.accessToken
    ├── HTTP Header Manager: Authorization: Bearer ${token}
    ├── HTTP Request: POST /api/orders
    │   └── Response Assertion: code = 201
    └── Uniform Random Timer: 2-5 s
```
```bash
jmeter -n -t checkout.jmx -l results.jtl -e -o report/
```

## Guardrails
- Never keep real credentials in CSV files committed to the repo.
- A sampler without an assertion can report success for an error page; add assertions.
- Generate load from enough machines; one overloaded load generator measures itself.
