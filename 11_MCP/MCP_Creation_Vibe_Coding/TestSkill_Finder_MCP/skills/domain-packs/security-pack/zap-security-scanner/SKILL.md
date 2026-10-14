---
name: zap-security-scanner
description: >-
  Sets up OWASP ZAP dynamic security scans (DAST) for web apps and APIs. Use when a team says
  "add a ZAP scan to CI", "run a baseline security scan", "scan our staging site", or
  "triage these ZAP alerts". Produces a passive baseline scan for every pipeline run, an
  approved active scan for scheduled runs, authentication setup, a rules file to tune false
  positives, and a triage table — pointed only at targets the team owns or may test.
license: MIT
metadata:
  author: AiTester
  pack: security
  version: 1.0.0
---

# ZAP Security Scanner

You run **automated security scanning that the team will keep using** — quiet enough to trust,
with alerts triaged instead of ignored.

## When to use
- A web app or API needs regular automated security checks in CI.
- A ZAP report exists with many alerts and the team needs to know which ones matter.

## Workflow
1. **Confirm the target and permission** — the URL of a test environment the team owns; never
   scan third-party sites or production without written approval.
2. **Baseline scan (passive) in CI** — spiders the app and reports issues without attacking it:
   `docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t https://staging.example.test -r zap-report.html`.
3. **API scan** — `zap-api-scan.py` with the OpenAPI definition to cover endpoints the spider
   cannot find.
4. **Active scan (full)** — `zap-full-scan.py` only on scheduled runs, against an approved
   environment with test data, because it sends attack traffic.
5. **Authentication** — configure the scan context or a session token so protected pages are
   covered; confirm with the report that authenticated URLs were reached.
6. **Tune and gate** — a rules file (`-c rules.tsv`) marks each alert IGNORE, WARN or FAIL;
   fail the pipeline only on agreed high-risk alerts.
7. **Triage** — every alert gets a decision: fix, accepted risk with an owner, or false positive
   with the reason.

## Output shape
```
## ZAP Triage — staging, baseline scan <date>
| Alert | Risk | URL | Decision | Owner |
|-------|------|-----|----------|-------|
| Content Security Policy header not set | Medium | / | fix | web team |
| Cookie without SameSite attribute | Low | /login | fix | auth team |
| Information disclosure - suspicious comments | Info | /app.js | false positive: build comment | — |
Gate: FAIL on High alerts · WARN on Medium · rules in .zap/rules.tsv
```

## Guardrails
- Scan only targets you own or have written permission to scan.
- Active scans can change data; use test environments and test accounts.
- A suppressed alert needs a recorded reason; never suppress to make the build green.
