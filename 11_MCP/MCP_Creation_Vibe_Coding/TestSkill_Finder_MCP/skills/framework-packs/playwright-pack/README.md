# Playwright pack

A framework pack: 11 skills that plug into the STLC phases. Each folder holds a `SKILL.md`: a short header plus the instructions an AI assistant follows.

| Skill | What it does | From |
|---|---|---|
| [pw-accessibility-auditor](pw-accessibility-auditor/SKILL.md) | Integrates automated accessibility checks into Playwright tests using axe-core. | skillmasterclass |
| [pw-api-tester](pw-api-tester/SKILL.md) | Designs and generates API tests using Playwright's request context. | skillmasterclass |
| [pw-ci-configurator](pw-ci-configurator/SKILL.md) | Generates CI configuration (GitHub Actions) for a Playwright suite. | skillmasterclass |
| [pw-fixture-designer](pw-fixture-designer/SKILL.md) | Designs custom Playwright test fixtures (auth/session, seeded data, page objects) with correct setup/teardown and scope. | skillmasterclass |
| [pw-flaky-debugger](pw-flaky-debugger/SKILL.md) | Diagnoses a flaky Playwright test and proposes web-first fixes. | skillmasterclass |
| [pw-locator-fixer](pw-locator-fixer/SKILL.md) | Scans a Playwright spec or Page Object for brittle locators and rewrites them to resilient ones. | skillmasterclass |
| [pw-network-mocker](pw-network-mocker/SKILL.md) | Designs Playwright route interception and mocking. | skillmasterclass |
| [pw-page-object-builder](pw-page-object-builder/SKILL.md) | Builds a Playwright Page Object Model class from a page or URL. | skillmasterclass |
| [pw-test-generator](pw-test-generator/SKILL.md) | Generates a Playwright (TypeScript) test spec from a described user flow or scenario. | skillmasterclass |
| [pw-trace-analyzer](pw-trace-analyzer/SKILL.md) | Analyzes a Playwright trace.zip or test failure to pinpoint the root cause. | skillmasterclass |
| [pw-visual-regression](pw-visual-regression/SKILL.md) | Sets up Playwright visual/screenshot regression testing. | skillmasterclass |

Search them by keyword with the [Test Skill Finder MCP](../../../README.md), or install one in Claude Code by copying
its folder to `~/.claude/skills/`.
