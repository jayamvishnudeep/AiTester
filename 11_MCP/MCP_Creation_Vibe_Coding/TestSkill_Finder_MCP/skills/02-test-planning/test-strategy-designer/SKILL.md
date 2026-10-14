---
name: test-strategy-designer
description: >-
  Design a test strategy for a product, release or team. Use when a QA lead says "write a
  test strategy", "how should we test this product", "define our test approach", or needs
  test levels, test types, automation scope, environments, tools and quality gates agreed
  before planning starts. Produces a strategy document with the reason behind each choice
  and the decisions still open for the team. Sits above a test plan.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Planning
  version: 1.0.0
---

# Test Strategy Designer

You draft the **testing approach a team commits to** — the "how we test" that individual test
plans follow. Every choice comes with its reason; open decisions stay open.

## When to use
- A new product, major release or new team needs an agreed approach to testing.
- Someone asks "what should we automate", "which test levels do we need", "what are our
  quality gates".
- A test plan is being written but there is no strategy to anchor it.

## Workflow
1. **Gather context** — product type, architecture (web, mobile, APIs, data), users, release
   cadence, regulations, team skills, current tooling, known pain points. Ask for what is
   missing instead of assuming it.
2. **Choose test levels** — unit, component, API/integration, end-to-end, and who owns each.
   Shape them as a pyramid: each check at the lowest level that can catch the bug.
3. **Choose test types by risk** — functional, regression, performance, security,
   accessibility, compatibility, usability, data migration — each justified by a risk.
4. **Set the automation scope** — what is automated, at which level, with which framework,
   and what stays manual (exploratory, usability, one-off checks).
5. **Define environments and data** — which environment per level, test data sources,
   masking of production data.
6. **Define quality gates** — entry and exit criteria per level, CI gates (what blocks a merge
   or a release), defect severity rules.
7. **Metrics and reporting** — what is measured and who sees it.
8. **List the open decisions** for the team.

## Output shape
```
## Test Strategy — <product / release>
1. Context & quality goals
2. Test levels & ownership (pyramid)
3. Test types, each with the risk it addresses
4. Automation approach (scope, frameworks, CI)
5. Environments & test data
6. Quality gates (entry / exit / CI / release)
7. Defect management & severity rules
8. Metrics & reporting
9. Risks, assumptions, open decisions
--- HUMAN REVIEW GATE --- "Agree or change these decisions before test plans rely on them"
```

## Guardrails
- Tie every test type to a risk; "we always do it" is not a reason.
- Do not promise coverage numbers or timelines the team has not agreed.
- Keep it short enough to be read: a strategy nobody reads is not a strategy.
