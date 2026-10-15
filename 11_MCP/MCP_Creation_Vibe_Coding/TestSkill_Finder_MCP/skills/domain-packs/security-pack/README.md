# Security pack

A domain pack: 6 skills that plug into the STLC phases. Each folder holds a `SKILL.md`: a short header plus the instructions an AI assistant follows.

| Skill | What it does | From |
|---|---|---|
| [auth-session-tester](auth-session-tester/SKILL.md) | Designs tests for authentication and session management. | added here |
| [dependency-vulnerability-scanner](dependency-vulnerability-scanner/SKILL.md) | Finds and triages vulnerable third-party dependencies and container images (software composition analysis). | added here |
| [owasp-web-security-tester](owasp-web-security-tester/SKILL.md) | Plans authorized web application security tests based on the OWASP Top 10 (2021). | added here |
| [secrets-leak-detector](secrets-leak-detector/SKILL.md) | Detects leaked secrets (API keys, tokens, passwords, private keys) in code, history and CI logs, and plans the response. | added here |
| [threat-model-test-planner](threat-model-test-planner/SKILL.md) | Turns a threat model into security test cases. | added here |
| [zap-security-scanner](zap-security-scanner/SKILL.md) | Sets up OWASP ZAP dynamic security scans (DAST) for web apps and APIs. | added here |

Search them by keyword with the [Test Skill Finder MCP](../../../README.md), or install one in Claude Code by copying
its folder to `~/.claude/skills/`.
