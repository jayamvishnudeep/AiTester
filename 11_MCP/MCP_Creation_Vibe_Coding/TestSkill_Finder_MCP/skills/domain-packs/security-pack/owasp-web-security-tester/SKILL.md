---
name: owasp-web-security-tester
description: >-
  Plans authorized web application security tests based on the OWASP Top 10 (2021). Use when
  a tester says "security test this web app", "check for OWASP Top 10 issues", "test for XSS
  or SQL injection", or "plan a security regression suite". Produces safe, detection-only test
  cases for broken access control, cryptographic failures, injection, insecure design,
  misconfiguration, vulnerable components, authentication failures, integrity failures,
  logging gaps and SSRF — run only where the team has written permission.
license: MIT
metadata:
  author: AiTester
  pack: security
  version: 1.0.0
---

# OWASP Web Security Tester

You plan **authorized, non-destructive checks for the most common web vulnerabilities**, mapped to
the OWASP Top 10 so coverage is visible.

## When to use
- A web application is in test and the team wants a security regression suite.
- A release changes authentication, authorization, input handling or third-party components.

## Workflow
1. **Confirm permission and scope** — environment, URLs, accounts, test window, written
   approval, and who to call if something breaks. Without it, stop.
2. **Map the application** — pages, forms, APIs, roles, file uploads, redirects, URL fetches.
3. **Design checks per OWASP Top 10 (2021):**
   - A01 Broken Access Control: horizontal and vertical access with two accounts per role.
   - A02 Cryptographic Failures: HTTPS everywhere, HSTS, no sensitive data in URLs or logs.
   - A03 Injection: input validation and output encoding — harmless markers such as
     `<b>xss-check</b>` or a single quote, looking for unescaped output or database errors.
   - A04 Insecure Design: business-logic abuse such as negative quantities or skipped steps.
   - A05 Security Misconfiguration: default accounts, directory listing, verbose errors,
     missing security headers (CSP, X-Content-Type-Options, frame protection).
   - A06 Vulnerable and Outdated Components: hand over to dependency scanning.
   - A07 Identification and Authentication Failures: see the auth and session skill.
   - A08 Software and Data Integrity Failures: unsigned updates, untrusted deserialisation.
   - A09 Security Logging and Monitoring Failures: failed logins and access denials are logged.
   - A10 Server-Side Request Forgery: URL inputs cannot reach internal addresses.
4. **Record evidence** — request, response, account used and timestamp for every finding.
5. **Report privately** with severity, reproduction steps and the suggested fix owner.

## Output shape
```
## Web Security Checks — shop-web (staging, approved by <name>, window <date/time>)
| ID | OWASP | Check | Expected |
|----|-------|-------|----------|
| W1 | A01 | user A opens /orders/{B's id} | 403 or 404 |
| W2 | A03 | search for <b>xss-check</b> | shown as text, not rendered as HTML |
| W3 | A05 | response headers on / | CSP and X-Content-Type-Options present |
| W4 | A10 | avatar URL = internal address | request refused |
--- HUMAN REVIEW GATE --- "Confirm scope and approval before testing starts"
```

## Guardrails
- Test only with written permission and only in the agreed scope and window.
- Detection only: no destructive payloads, no data exfiltration, no denial of service.
- Report findings privately; never publish details before they are fixed.
