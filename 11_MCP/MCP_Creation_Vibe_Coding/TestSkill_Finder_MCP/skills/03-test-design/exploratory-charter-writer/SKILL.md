---
name: exploratory-charter-writer
description: >-
  Write session-based exploratory testing charters. Use when a tester says "plan an
  exploratory session", "write charters for this feature", "what should I explore", or wants
  structured exploration of a new or risky area. Produces time-boxed charters in "Explore
  <target> with <resources> to discover <information>" form, test ideas from heuristics such
  as SFDPOT and testing tours, and a session-notes template for findings, bugs and questions.
  Complements scripted tests; does not replace them.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Design
  version: 1.0.0
---

# Exploratory Charter Writer

You plan **focused exploration with a mission and a timebox**, so exploratory testing finds the
bugs scripts miss and still leaves evidence a lead can review.

## When to use
- A feature is new, changed in many places, or poorly specified.
- Scripted tests pass but the team suspects problems; a release needs a quick risk sweep.

## Workflow
1. **Understand the area** — what changed, who uses it, known risks and past bugs.
2. **Write 3-6 charters**, one line each:
   `Explore <target> with <resources/tools/data> to discover <information/risk>`.
   One charter per risk; each fits a 60-90 minute session.
3. **Add test ideas per charter** using heuristics:
   - SFDPOT: Structure, Function, Data, Platform, Operations, Time.
   - Tours: money tour (main value flows), back-alley tour (rarely used features),
     garbage-collector tour (cleanup and deletion), interruption tour (network loss, refresh).
   - Personas: first-time user, power user, keyboard-only or screen-reader user.
4. **Define the session record** — timebox, setup, notes, bugs (with steps), questions, areas
   not reached, and the split of time between testing, setup and bug investigation.
5. **Plan the debrief** — the questions the lead asks after each session.

## Output shape
```
## Exploratory Charters — <feature>
C1 (60 min) Explore checkout with expired and declined test cards to discover how payment
   errors are reported and recovered
   Ideas: double-click Pay · browser back after paying · switch card mid-flow · slow network
C2 (90 min) Explore order history with large accounts to discover paging and sorting limits
### Session record template
Charter · Tester · Start/End · Notes · Bugs (steps + evidence) · Questions · Not covered
--- HUMAN REVIEW GATE --- "Pick and order the charters for the sessions available"
```

## Guardrails
- One mission per charter; a charter that covers everything covers nothing.
- Bugs found in a session still need full reproduction steps before they are filed.
- Report what was not explored as clearly as what was.
