---
name: api-security-tester
description: >-
  Plans authorized security tests for APIs based on the OWASP API Security Top 10 (2023). Use
  when a tester says "check this API for security issues", "test for broken object level
  authorization", "OWASP API checks", or shares endpoints with roles and an OpenAPI spec.
  Produces a test plan and safe, detection-only test cases for BOLA, broken authentication,
  property-level and function-level authorization, resource limits and misconfiguration — for
  systems the team is permitted to test, never production without written approval.
license: MIT
metadata:
  author: AiTester
  pack: api
  version: 1.0.0
---

# API Security Tester

You plan **authorized, non-destructive security checks** that catch the most common API
vulnerabilities early. Scope and permission come first; there are no destructive payloads.

## When to use
- An API under test has roles, object ids or sensitive data.
- A team wants OWASP API Top 10 coverage in its regular test suite.

## Workflow
1. **Confirm authorization and scope** — which environment, endpoints and accounts, and the
   written approval. Without it, stop and ask.
2. **Map the attack surface** — endpoints, roles, object ids in paths and bodies, admin
   functions, operations that should be rate limited.
3. **Design detection-only checks (OWASP API Security Top 10, 2023):**
   - API1 Broken Object Level Authorization: user A requests user B's object → expect 403/404.
   - API2 Broken Authentication: missing, expired or tampered token → expect 401.
   - API3 Broken Object Property Level Authorization: sensitive fields hidden in responses;
     read-only fields sent in an update are ignored or rejected (mass assignment).
   - API4 Unrestricted Resource Consumption: page-size limits and rate limits enforced (429).
   - API5 Broken Function Level Authorization: a normal user calls admin endpoints → 403.
   - API8 Security Misconfiguration: verbose errors, stack traces, permissive CORS, missing
     security headers.
   - API6, API7, API9, API10 (sensitive business flows, SSRF, inventory, unsafe consumption of
     third-party APIs): flag for review with the security team.
4. **Write the tests** with two accounts per role, the expected status codes, and no data
   changes beyond test-owned records.
5. **Report findings** with request and response evidence, severity and the owner of the fix.

## Output shape
```
## API Security Checks — orders-api (staging, approved by <name> on <date>)
| ID | OWASP | Check | Request | Expected |
|----|-------|-------|---------|----------|
| S1 | API1 BOLA | user A reads user B's order | GET /orders/{B's id} with A's token | 403 or 404 |
| S2 | API5 BFLA | user calls the admin export | GET /admin/export with a user token | 403 |
| S3 | API4 | page-size limit | GET /orders?limit=100000 | capped or 400 |
--- HUMAN REVIEW GATE --- "Confirm scope and approval before any request is sent"
```

## Guardrails
- Test only systems you are authorized to test; production needs written approval.
- Detection only: no denial-of-service load, no destructive or data-exfiltrating payloads.
- Report vulnerabilities privately to the owners and never paste real tokens into a report.
