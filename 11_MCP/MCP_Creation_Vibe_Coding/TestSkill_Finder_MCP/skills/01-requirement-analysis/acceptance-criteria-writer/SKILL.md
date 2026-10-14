---
name: acceptance-criteria-writer
description: >-
  Turn a user story into clear Given/When/Then acceptance criteria. Use when a tester, BA or
  product owner says "write acceptance criteria for this story", "make this story testable",
  "add AC", or pastes a story in "As a ... I want ... so that ..." form. Produces happy-path,
  negative, boundary and permission criteria in Gherkin-style language and lists every
  assumption it had to make, for the product owner to accept or correct.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Requirement Analysis
  version: 1.0.0
---

# Acceptance Criteria Writer

You draft **acceptance criteria the product owner must confirm** — a proposal that makes the
story testable, never the final word on what the product does.

## When to use
- A story has no acceptance criteria, or only a one-line goal.
- Someone wants Given/When/Then criteria before refinement or sprint planning.

## Workflow
1. **Restate the story** — role, capability, value. If any of the three is missing, ask.
2. **List the rules hidden in the story** — limits, validations, permissions, states.
3. **Write criteria, one behaviour each:**
   - Happy path: the main outcome for the main role.
   - Negative: invalid input, missing data, failure of a dependency.
   - Boundary: minimum, maximum, empty, just above or below a limit.
   - Permissions: what other roles can and cannot do.
4. **Keep them declarative** — describe behaviour, not clicks ("When she submits the form",
   not "When she clicks the blue button at the bottom").
5. **Mark every assumption** with ⚠️ so the product owner can correct it.

## Output shape
```
## Acceptance Criteria — <story>
AC1 (happy path)
  Given a registered user with items in the cart
  When she pays with a valid card
  Then the order is confirmed and a confirmation email is sent

AC2 (negative)
  Given a registered user with items in the cart
  When the card is declined
  Then she sees the decline reason and no order is created

AC3 (boundary) ⚠️ assumes a limit of 10 items per order
  Given a cart with 10 items
  When she adds an 11th item
  Then she is told the limit is 10 items

Assumptions to confirm: ...
--- HUMAN REVIEW GATE --- "Accept, edit or reject each AC before it goes into the story"
```

## Guardrails
- Never present an assumption as a rule; flag it.
- One behaviour per criterion; split anything joined with "and also".
- Do not add scope the story does not ask for; list ideas separately as possible follow-ups.
