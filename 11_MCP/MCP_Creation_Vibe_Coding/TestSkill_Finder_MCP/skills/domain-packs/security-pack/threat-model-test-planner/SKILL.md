---
name: threat-model-test-planner
description: >-
  Turns a threat model into security test cases. Use when a team says "threat model this
  feature", "what could an attacker do here", "plan security testing with STRIDE", or shares
  an architecture or data-flow diagram. Identifies assets, entry points and trust boundaries,
  walks each element through STRIDE (spoofing, tampering, repudiation, information disclosure,
  denial of service, elevation of privilege), and produces prioritised, authorized test cases
  with the mitigation each one verifies.
license: MIT
metadata:
  author: AiTester
  pack: security
  version: 1.0.0
---

# Threat Model Test Planner

You connect **"what could go wrong" to "how we prove it doesn't"** — every important threat gets
a mitigation and a test that checks the mitigation.

## When to use
- A new feature handles sensitive data, money, authentication or external input.
- Security testing exists but nobody knows which threats it covers.

## Workflow
1. **Draw the system** — a simple data-flow diagram: users, processes, data stores, external
   systems, and the trust boundaries between them. Ask for the architecture; do not guess it.
2. **List assets and entry points** — personal data, credentials, payments, admin functions;
   APIs, forms, file uploads, webhooks, message queues.
3. **Apply STRIDE per element crossing a boundary:**
   - Spoofing → authentication; Tampering → integrity checks and validation;
   - Repudiation → audit logs; Information disclosure → access control and encryption;
   - Denial of service → limits and quotas; Elevation of privilege → authorization.
4. **Rate each threat** — likelihood and impact (or the team's scheme such as CVSS-like
   ratings) and name the expected mitigation.
5. **Write a test per mitigation** — what to try, with which account and data, and the
   expected safe behaviour. Detection-only, in authorized environments.

## Output shape
```
## Threat Model → Tests — file upload service
| Threat (STRIDE) | Entry point | Mitigation | Test | Expected | Priority |
|-----------------|-------------|------------|------|----------|----------|
| T: malicious file replaces another user's file | PUT /files/{id} | ownership check | user A updates user B's file id | 403 | High |
| I: upload readable without auth | GET /files/{id} | signed, expiring URLs | open URL after expiry | 403 | High |
| D: very large upload | POST /files | 20 MB size limit | upload 21 MB | 413 | Medium |
--- HUMAN REVIEW GATE --- "Security owner confirms the model and the priorities"
```

## Guardrails
- Test only systems and accounts you are authorized to use.
- A threat without a mitigation is a finding for the team, not something to test around.
- Keep the model up to date when the architecture changes.
