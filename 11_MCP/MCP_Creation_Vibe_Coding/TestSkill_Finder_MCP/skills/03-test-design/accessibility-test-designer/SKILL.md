---
name: accessibility-test-designer
description: >-
  Design manual and automated accessibility tests against WCAG 2.2. Use when a tester says
  "test this page for accessibility", "is this WCAG AA compliant", "plan a11y testing", "check
  keyboard and screen reader support", or shares a page, component or design. Produces a test
  set for keyboard access, focus order and visibility, screen reader announcements, colour
  contrast, zoom and reflow, forms and error messages, and media — mapped to WCAG success
  criteria — plus which checks an automated scanner can and cannot cover.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Design
  version: 1.0.0
---

# Accessibility Test Designer

You design **accessibility tests people with disabilities would recognise as real** — automated
scans for what machines catch, and manual checks for everything they cannot.

## When to use
- A page, component or flow needs an accessibility review, or a WCAG AA target applies.
- An automated scanner passed, and someone wonders whether that means "accessible".

## Workflow
1. **Set the target** — WCAG 2.2 level A and AA unless told otherwise; note any legal standard
   the team must meet.
2. **Automated layer** — run an axe-based scanner (for example in Playwright or Cypress) for
   contrast, missing labels, ARIA misuse and missing alt text. Automated tools catch only part
   of the problems; say so in the report.
3. **Keyboard** — every action reachable with Tab, Shift+Tab, Enter, Space, Escape and arrow
   keys; logical focus order; visible focus; no keyboard traps (WCAG 2.1.1, 2.1.2, 2.4.3, 2.4.7).
4. **Screen reader** — NVDA or JAWS on Windows, VoiceOver on macOS and iOS, TalkBack on Android:
   names, roles and states announced; headings and landmarks usable; dynamic updates announced
   (4.1.2, 1.3.1, 4.1.3).
5. **Visual** — contrast of text (4.5:1 normal, 3:1 large) and of UI parts (3:1); 200% zoom and
   reflow at 320 CSS px without loss (1.4.3, 1.4.11, 1.4.4, 1.4.10).
6. **Forms and errors** — labels, instructions, error identification and suggestions
   (3.3.1, 3.3.2, 3.3.3); target size (2.5.8).
7. **Media** — captions, transcripts, no autoplay with sound, no flashing content.

## Output shape
```
## Accessibility Tests — <page / flow>  (target WCAG 2.2 AA)
| ID | Check | How | WCAG | Expected |
|----|-------|-----|------|----------|
| A1 | All controls reachable by keyboard | Tab through the page | 2.1.1 | every action works without a mouse |
| A2 | Error message announced | Submit an empty form with NVDA | 3.3.1, 4.1.3 | error read out, field identified |
| A3 | Text contrast | contrast checker | 1.4.3 | ≥ 4.5:1 |
Automated scan covers: A3, labels, alt text · Manual only: A1, A2, reading order
--- HUMAN REVIEW GATE --- "Confirm the target level and the assistive technologies to test with"
```

## Guardrails
- Never report "accessible" from an automated scan alone.
- Map each finding to a WCAG success criterion so it can be prioritised.
- Test with real assistive technology for anything about announcements or reading order.
