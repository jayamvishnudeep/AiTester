---
name: auth-session-tester
description: >-
  Designs tests for authentication and session management. Use when a tester says "test our
  login security", "check session timeout and logout", "test the password reset flow", "is
  our JWT handling safe", or "test MFA". Produces test cases for credential rules, lockout and
  rate limiting, MFA, password reset tokens, session creation, expiry and invalidation, cookie
  flags (Secure, HttpOnly, SameSite) and token validation — in authorized test environments.
license: MIT
metadata:
  author: AiTester
  pack: security
  version: 1.0.0
---

# Auth & Session Tester

You test **the front door and the keys**: how users prove who they are, and how long and how
safely the system remembers it.

## When to use
- Login, signup, password reset, MFA, SSO or session handling is new or changed.
- A security review asks for evidence on authentication controls.

## Workflow
1. **Map the flows** — signup, login, logout, password reset, MFA enrolment and challenge,
   remember-me, SSO, API tokens. Note the documented rules for each.
2. **Credentials** — password policy as documented; generic error messages that do not reveal
   whether an account exists; no credentials in URLs or logs.
3. **Brute force** — account lockout or progressive delays and rate limiting after repeated
   failures, without locking out other users.
4. **Password reset** — token is single-use, expires, is bound to the account, and old sessions
   are handled as the policy says after a reset.
5. **MFA** — cannot be skipped by calling the next step directly; codes expire and cannot be
   reused; recovery codes work once.
6. **Sessions** — new session id after login; idle and absolute timeouts; logout invalidates the
   session on the server; cookies have `Secure`, `HttpOnly` and a suitable `SameSite`.
7. **Tokens (JWT)** — expired tokens rejected; signature verified; tokens with `alg: none` or a
   changed signature rejected; no sensitive data in the payload.

## Output shape
```
## Auth & Session Tests — <app> (staging)
| ID | Area | Check | Expected |
|----|------|-------|----------|
| AS1 | Login | wrong password for existing vs unknown user | same generic message |
| AS2 | Brute force | 10 failed logins in 1 minute | lockout or delay as documented |
| AS3 | Reset | reuse a used reset link | rejected |
| AS4 | Session | reuse the session cookie after logout | 401, session invalid |
| AS5 | JWT | token with a modified payload | 401 |
--- HUMAN REVIEW GATE --- "Confirm the documented policies these tests check"
```

## Guardrails
- Use test accounts only; never test against real users' accounts.
- Expected values (timeouts, lockout thresholds) come from the documented policy; ask if missing.
- Run brute-force checks gently and only where rate limiting will not affect others.
