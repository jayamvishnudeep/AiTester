---
name: bdd-scenario-writer
description: >-
  Write BDD feature files in Gherkin for Cucumber, SpecFlow, Behave or playwright-bdd. Use
  when a team says "write Gherkin for this story", "create feature files", "convert these
  acceptance criteria to BDD", or needs Given/When/Then scenarios that business and
  developers both read. Produces declarative scenarios, Scenario Outlines with Examples for
  data variations, a Background for shared setup, and tags — without UI-click steps.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Design
  version: 1.0.0
---

# BDD Scenario Writer

You write **feature files the business can read and the automation can bind to** — behaviour
first, implementation details out.

## When to use
- Acceptance criteria exist and the team practises BDD (Cucumber, Cucumber-JVM, SpecFlow,
  Behave, playwright-bdd).
- Existing feature files are imperative ("click", "type") and need to become declarative.

## Workflow
1. **One feature per capability**, with a short description in business terms.
2. **Background** only for setup every scenario in the file needs; keep it short.
3. **Declarative scenarios** — Given (state), When (one action), Then (observable outcome).
   Business language, no selectors, no "click the button".
4. **Scenario Outline + Examples** for data variations instead of copied scenarios; name the
   columns after the domain ("plan", "seats", "result").
5. **Tags** for selection: `@smoke`, `@regression`, `@JIRA-123`, `@wip`.
6. **Reuse step wording** — the same phrase for the same step keeps step definitions few.

## Output shape
```gherkin
@billing @JIRA-482
Feature: Plan upgrade
  Account owners can move to a bigger plan and pay only the difference.

  Background:
    Given an account owner on the "Starter" plan

  @smoke
  Scenario: Upgrade with a saved card
    When she upgrades to the "Growth" plan
    Then she is charged the prorated difference
    And the new plan limits apply immediately

  Scenario Outline: Seat limits per plan
    When she invites <seats> team members on the "<plan>" plan
    Then the invitation is <result>

    Examples:
      | plan    | seats | result   |
      | Starter | 3     | accepted |
      | Starter | 4     | rejected |
```

## Guardrails
- One When per scenario; two actions usually mean two scenarios.
- No UI mechanics in steps; they belong in step definitions or page objects.
- Do not invent business rules for Examples tables; use the acceptance criteria and flag gaps.
- The feature file is a draft for the product owner, developer and tester to review together.
