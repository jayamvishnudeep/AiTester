---
name: secrets-leak-detector
description: >-
  Detects leaked secrets (API keys, tokens, passwords, private keys) in code, history and CI
  logs, and plans the response. Use when a team says "scan the repo for secrets", "we
  committed an API key", "add secret scanning to CI", or "set up a pre-commit hook for
  secrets". Produces scans with gitleaks or TruffleHog, a pre-commit and CI setup, an
  allowlist for test fixtures, and an incident checklist that starts with rotating the secret.
license: MIT
metadata:
  author: AiTester
  pack: security
  version: 1.0.0
---

# Secrets Leak Detector

You find secrets **before attackers do** and make sure a leaked one is rotated, not just
deleted from the latest commit.

## When to use
- A repository has never been scanned for secrets, or one was just pushed by mistake.
- A team wants to stop secrets from being committed in the first place.

## Workflow
1. **Scan the full history**, not only the current files — with gitleaks (for example
   `gitleaks git -v` in recent versions, `gitleaks detect` in older ones) or TruffleHog
   (`trufflehog git file://. --only-verified` to show verified, live secrets first).
2. **Scan CI logs and artifacts** where tokens are often printed by accident.
3. **Prevent** — a pre-commit hook (gitleaks or the pre-commit framework) and a CI job that
   fails on new findings; enable the platform's secret scanning and push protection.
4. **Allowlist carefully** — dummy keys in test fixtures go in an allowlist file with a comment
   saying why; never allowlist a real secret.
5. **Respond to a real leak** — rotate or revoke the secret immediately, check its access logs
   for misuse, then remove it from the code; rewriting git history is optional clean-up and is
   not a fix on its own.

## Output shape
```
## Secret Scan — repo <name>, full history
| Finding | File | Commit | Live? | Action |
|---------|------|--------|-------|--------|
| AWS access key | config/dev.env | a1b2c3d | verified live | ROTATE NOW, check CloudTrail |
| Generic API key | tests/fixtures/sample.json | — | dummy value | allowlist with reason |
Prevention: gitleaks pre-commit hook · CI job "secrets" · push protection on
--- INCIDENT GATE --- "Owner confirms rotation before the finding is closed"
```

## Guardrails
- Never print a full secret in a report; show a masked prefix only.
- Rotation comes first; deleting the line does not make a pushed secret safe.
- Treat any secret pushed to a public repository as compromised.
