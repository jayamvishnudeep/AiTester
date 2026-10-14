---
name: automation-framework-selector
description: >-
  Recommend a test automation framework for a project. Use when a team asks "Playwright,
  Cypress or Selenium?", "which framework should we use for UI or API automation", "choose a
  test stack", or is starting automation from scratch. Compares the candidates against the
  team's real constraints (languages, browsers, mobile, CI, skills, budget) in a weighted
  decision matrix and recommends one with the trade-offs stated. A proposal for the team to
  decide, never a mandate.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Planning
  version: 1.0.0
---

# Automation Framework Selector

You make the framework choice **explicit and reviewable** — a weighted comparison against the
team's constraints, ending in a recommendation the team owns.

## When to use
- Automation is starting, or a team is considering replacing its current framework.
- Someone asks for a comparison of Playwright, Cypress, Selenium, Appium, REST Assured and so on.

## Workflow
1. **Collect the constraints** — application type (web, mobile, API, desktop), browsers that
   must be covered (including Safari/WebKit), team languages (Java, TypeScript, Python, C#),
   existing CI, parallel and cross-browser needs, test data and auth setup, budget for paid
   services, timeline.
2. **Pick 2-4 candidates** that fit the application type — web UI: Playwright, Cypress,
   Selenium WebDriver; API: Playwright's request context, REST Assured, Postman/Newman;
   mobile: Appium.
3. **Weight the criteria with the team** (weights add up to 100) — language fit, browser
   coverage, stability (auto-waiting), debugging tools, parallelism and CI, community and
   hiring, learning curve, licence and cost.
4. **Score each candidate 1-5 per criterion** with one line of evidence. Well-known facts:
   Playwright drives Chromium, Firefox and WebKit with auto-waiting and a trace viewer;
   Cypress runs inside the browser (Chromium-family and Firefox, WebKit experimental) with
   strong debugging, in JavaScript/TypeScript only; Selenium supports most languages and real
   browsers through WebDriver and Grid, leaving more wait handling to the team.
5. **Recommend** the highest weighted total, state what the team gives up, and name the proof
   of concept that would confirm it (for example, automate five real flows in the top two).

## Output shape
```
## Framework Selection — <project>
Constraints: TypeScript team · Chrome + Safari required · GitHub Actions · 8 weeks
| Criterion (weight) | Playwright | Cypress | Selenium |
|--------------------|-----------|---------|----------|
| Language fit (25) | 5 | 5 | 3 |
| Browser coverage (25) | 5 (WebKit) | 3 (WebKit experimental) | 4 |
| Stability (20) | 5 | 4 | 3 |
| ... | | | |
| Weighted total | 4.6 | 4.0 | 3.4 |
Recommendation: Playwright — trade-off: ...
Proof of concept to confirm: ...
--- HUMAN REVIEW GATE --- "Confirm the weights and run the proof of concept before committing"
```

## Guardrails
- Score against the team's constraints, not general popularity.
- Do not state version-specific capabilities you have not confirmed; mark them for checking.
- Always end with a proof of concept: a framework choice is cheap to test and expensive to undo.
