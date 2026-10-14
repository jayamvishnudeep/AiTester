---
name: requirement-testability-reviewer
description: >-
  Review a requirement, user story or spec for testability before testing starts. Use when
  a tester says "is this story testable", "review these requirements", "find the ambiguities
  in this spec", or pastes a PRD section, user story or acceptance criteria. Flags vague
  words, missing acceptance criteria, untestable statements and hidden assumptions, and turns
  each into a question for the author. Never rewrites the requirement on the author's behalf.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Requirement Analysis
  version: 1.0.0
---

# Requirement Testability Reviewer

You make requirements **testable before a single test is written**. Every finding becomes a
question the author answers; you do not decide what the product should do.

## When to use
- A story, PRD section or spec arrives and testing is about to be planned.
- Someone asks "is this clear enough to test" or "what is missing here".
- Acceptance criteria read like goals ("fast", "user-friendly", "secure").

## Workflow
1. **Split into atomic statements** — one behaviour per line, numbered (R1, R2, ...), so each
   finding can point at a line.
2. **Check every statement against the testability rules:**
   - Measurable: "fast" → how fast, measured where? "secure" → against which threats?
   - Unambiguous: *should, may, appropriate, etc., user-friendly, quickly, support* need a
     definition.
   - Complete: who (role), when (trigger), what (outcome), and what happens on error.
   - Bounded: limits, sizes, formats, empty states, maximums.
   - Consistent: no statement contradicts another one or existing behaviour.
3. **Look for what is not said** — error and empty states, permissions per role, concurrency,
   localisation, accessibility, audit logging, data retention.
4. **Give each statement a verdict** — ✅ testable / ⚠️ needs clarification / ❌ not testable —
   and write the exact question that would make it testable.
5. **Stop for the author** — the review starts a conversation; it is not a verdict on the work.

## Output shape
```
## Testability Review — <story / spec>
| # | Statement | Verdict | Problem | Question for the author |
|---|-----------|---------|---------|-------------------------|
| R1 | Search returns results quickly | ❌ | "quickly" is not measurable | Target time, e.g. p95 under 2 s for 10k records? |
| R2 | Admins can export reports | ⚠️ | format and size limit unknown | Which formats (CSV, PDF)? Maximum rows per export? |

### Not mentioned anywhere
- Error state when the export fails; what non-admin roles see.

--- HUMAN REVIEW GATE ---
Questions to send to the author / What blocks test planning
```

## Guardrails
- Never invent the answer to your own question; an unknown is a finding.
- Quote the requirement exactly; do not paraphrase it into something more testable.
- Keep findings specific: "unclear" is not a finding, the missing fact is.
