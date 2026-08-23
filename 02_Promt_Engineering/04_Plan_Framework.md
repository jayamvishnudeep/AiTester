# Selenium/Java/Maven/TestNG Framework for Salesforce Login

## Context

`AiTester4X` is a prompt-engineering training workspace. `02_Promt_Engineering/00_Task1.md` sets the assignment ("Write a Selenium Code for the Salesforce login"), `01_RICE_POT_Template.md` is the blank RICE-POT template, and `02_RICE_POT.example.md` (currently empty, open in the IDE) is meant to hold a worked example of that template applied to Task1. The prompt the user pasted **is** that worked example — a fully-specified RICE-POT prompt whose payload asks for a production-grade Selenium automation suite against `login.salesforce.com/?locale=in`.

The user confirmed the goal: actually build the real Maven/Selenium/TestNG project the prompt describes, not just log it as documentation. No Selenium/Java project exists anywhere in the workspace yet — everything is created from scratch.

## Hard constraints from the prompt (non-negotiable)

- Page Object Model with **PageFactory** (`@FindBy`, constructor `PageFactory.initElements`, reusable action methods)
- **XPath-only** locators (`By.xpath` via `@FindBy(xpath = ...)`) — no `By.id`, `By.name`, `By.cssSelector`
- **No `Thread.sleep()`** anywhere — `WebDriverWait` / `ExpectedConditions` only
- Structured **try-catch** exception handling in both the Page Object and the test classes
- TestNG lifecycle annotations (`@Test` plus setup/teardown annotations)
- **No comments** in the generated Java code
- Deliverable is exactly: **1 Page Object class + 2 TestNG test classes** (valid-login suite, invalid-login suite) + the Maven project scaffold — nothing extra, no explanatory prose in the code files
- Credentials are external (user will supply real Salesforce username/password later) — must not hardcode a single "valid" credential pair baked into the test logic

## Project layout

New folder at the workspace root, `03_Selenium_Salesforce_Framework/` (keeps the existing numbered-lesson convention and marks this as the artifact produced by the Task1/RICE-POT exercise):

```
03_Selenium_Salesforce_Framework/
├── pom.xml
├── testng.xml
├── src/main/java/com/aitester/pages/LoginPage.java
├── src/test/java/com/aitester/tests/ValidLoginTest.java
├── src/test/java/com/aitester/tests/InvalidLoginTest.java
└── src/test/resources/config.properties
```

`testng.xml` and `config.properties` are part of "the Maven project" deliverable (scaffold/config), not extra Java classes, so they don't violate the "3 files only" output constraint.

## Design decisions

- **Selenium 4 built-in driver management** (Selenium Manager, Selenium ≥4.6) instead of adding a WebDriverManager dependency — keeps `pom.xml` minimal while still avoiding hardcoded driver paths.
- **Per-test browser isolation**: use `@BeforeMethod`/`@AfterMethod` (falls under the prompt's "`@BeforeTest` and others") to create/quit the driver around each `@Test`, so negative test cases (bad password, bad email, empty fields, etc.) don't leak state between each other. `@BeforeTest`/`@AfterTest` would share one driver across a whole `<test>` block in `testng.xml`, which is worse for isolating invalid-login assertions.
- **Externalized credentials**: `ValidLoginTest` reads username/password from `config.properties` (with System-property override, e.g. `-Dsf.username=...`), not from a literal string, since real valid Salesforce credentials aren't available here and the user said they'd supply their own later.
- **Exception handling**: every Page Object action method wraps its Selenium call in try-catch around explicit exception types (`TimeoutException`, `NoSuchElementException`) and rethrows a runtime exception with context; test methods wrap driver setup/navigation and assertions similarly, per the "[Critical]" instruction.
- **UI thoroughness**: `ValidLoginTest` checks page-level UI (title, URL, presence/visibility of username, password, remember-me checkbox, login button) plus a login attempt using the externalized creds. `InvalidLoginTest` covers: wrong password, wrong/unregistered username, malformed email format, empty username, empty password, both empty — each asserting the Salesforce error banner appears via `WebDriverWait`.
- **Locators**: real Salesforce login DOM attributes referenced *through XPath expressions* (e.g. `//input[@id='username']`), matching the pattern already given in the prompt's own Example block — this satisfies "XPath only" since the Selenium locator strategy used is `By.xpath`, even though the expression itself references an `id` attribute.

## Files to create

1. **`03_Selenium_Salesforce_Framework/pom.xml`** — Java 17 (or 11), `selenium-java` (4.x), `testng`, `maven-compiler-plugin`, `maven-surefire-plugin` wired to `testng.xml`.
2. **`src/main/java/com/aitester/pages/LoginPage.java`** — `@FindBy(xpath=...)` fields for username, password, remember-me checkbox, login button, and error-message element; constructor calling `PageFactory.initElements`; methods `enterUsername`, `enterPassword`, `toggleRememberMe`, `clickLogin`, `getErrorMessage`, `isLoginButtonDisplayed`, etc., each with try-catch and `WebDriverWait`-based waits.
3. **`src/test/java/com/aitester/tests/ValidLoginTest.java`** — `@BeforeMethod` driver setup + navigate to `https://login.salesforce.com/?locale=in`, UI element presence assertions, a login-attempt test using externalized credentials, `@AfterMethod` teardown, try-catch throughout.
4. **`src/test/java/com/aitester/tests/InvalidLoginTest.java`** — same lifecycle scaffolding; multiple `@Test` methods for each negative scenario, asserting the Salesforce error message displays.
5. **`src/test/resources/config.properties`** — placeholder `sf.username` / `sf.password` keys for the user to fill in with real creds.
6. **`03_Selenium_Salesforce_Framework/testng.xml`** — suite wiring both test classes.

No comments will be added to the Java files per the prompt's explicit instruction; this plan doc is the only place the rationale is recorded.

## Verification

- `mvn -q -f 03_Selenium_Salesforce_Framework/pom.xml compile test-compile` to confirm the project builds cleanly (requires Java + Maven on PATH — check first with `mvn -v`).
- `mvn -f 03_Selenium_Salesforce_Framework/pom.xml test` to actually run the suite against the live Salesforce login page (requires Chrome installed; will exercise both valid and invalid flows — the "valid" run will only truly pass once the user drops real credentials into `config.properties`).
- Manually review `InvalidLoginTest` output/report (`target/surefire-reports`) to confirm each negative scenario correctly asserts Salesforce's real error-banner text.
