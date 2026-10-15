# Selenium pack

A framework pack: 11 skills that plug into the STLC phases. Each folder holds a `SKILL.md`: a short header plus the instructions an AI assistant follows.

| Skill | What it does | From |
|---|---|---|
| [se-cross-browser-runner](se-cross-browser-runner/SKILL.md) | Sets up cross-browser Selenium execution across Chrome, Firefox, and Edge via TestNG parameters or a factory, plus a browser matrix. | skillmasterclass |
| [se-data-driven-designer](se-data-driven-designer/SKILL.md) | Designs data-driven Selenium tests with TestNG @DataProvider (or Excel/CSV/JSON sources), covering valid, invalid, and boundary data sets. | skillmasterclass |
| [se-driver-manager](se-driver-manager/SKILL.md) | Sets up browser driver management with Selenium Manager (built-in) or WebDriverManager, browser options, and a thread-safe driver factory. | skillmasterclass |
| [se-flaky-debugger](se-flaky-debugger/SKILL.md) | Diagnoses flaky Selenium tests — StaleElementReferenceException, timing and synchronization races, dynamic/late-rendering elements — and proposes robust fixes. | skillmasterclass |
| [se-framework-scaffolder](se-framework-scaffolder/SKILL.md) | Scaffolds a Maven Selenium framework — TestNG suite, base test, Page Object package, config loader, logging, and reporting hooks. | skillmasterclass |
| [se-grid-configurator](se-grid-configurator/SKILL.md) | Configures Selenium Grid 4 (hub-and-node or standalone, including Docker) and wires RemoteWebDriver for parallel and distributed runs. | skillmasterclass |
| [se-locator-strategist](se-locator-strategist/SKILL.md) | Recommends and repairs Selenium locator strategy — replaces brittle absolute XPath with By.id, By.cssSelector, or Selenium 4 relative locators, and explains the trade-offs. | skillmasterclass |
| [se-page-object-builder](se-page-object-builder/SKILL.md) | Builds a Page Object Model class in Java (PageFactory @FindBy or explicit locators) with action methods and a WebDriverWait for a given page. | skillmasterclass |
| [se-report-integrator](se-report-integrator/SKILL.md) | Integrates reporting (Allure or ExtentReports) into a Selenium + TestNG suite with listeners, screenshot-on-failure, and step logging. | skillmasterclass |
| [se-test-generator](se-test-generator/SKILL.md) | Generates a runnable Selenium 4 + TestNG test in Java from a plain-language scenario, using explicit waits and stable locators. | skillmasterclass |
| [se-wait-fixer](se-wait-fixer/SKILL.md) | Scans Selenium Java code for Thread.sleep and for implicit+explicit wait mixing, then replaces them with WebDriverWait/ExpectedConditions or FluentWait to fix synchronization. | skillmasterclass |

Search them by keyword with the [Test Skill Finder MCP](../../../README.md), or install one in Claude Code by copying
its folder to `~/.claude/skills/`.
