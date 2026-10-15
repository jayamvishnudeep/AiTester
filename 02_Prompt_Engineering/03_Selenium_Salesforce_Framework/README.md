# Selenium Salesforce Framework

The Maven project that the filled-in RICE-POT prompt in [`../02_RICE_POT.example.md`](../02_RICE_POT.example.md)
produced: Selenium 4 + TestNG tests for the Salesforce login page, built on a Page Object. How it came about is in
the [Prompt Engineering README](../README.md).

## Contents

| Path | What it is |
|---|---|
| [pom.xml](pom.xml) | Selenium Java 4.8.3, TestNG 7.7.1, the compiler and Surefire plugins (Java 10) |
| [testng.xml](testng.xml) | `SalesforceLoginSuite`: `ValidLoginTests` and `InvalidLoginTests` |
| [LoginPage.java](src/main/java/com/aitester/pages/LoginPage.java) | The Page Object: `@FindBy` locators for username, password, login button, Remember Me and the error message, a `WebDriverWait`, and actions such as `enterUsername`, `toggleRememberMe` and `doLogin` |
| [ValidLoginTest.java](src/test/java/com/aitester/tests/ValidLoginTest.java) | Logs in at `https://login.salesforce.com/?locale=in` with `sf.username` and `sf.password`, read from system properties first and `config.properties` second |
| [InvalidLoginTest.java](src/test/java/com/aitester/tests/InvalidLoginTest.java) | Invalid password, unregistered username, malformed username and empty username, each expecting the error message |
| [config.properties](src/test/resources/config.properties) | `sf.username` and `sf.password` — placeholders to replace with your own test account |

## Requirements

- JDK 10 or later, and Maven
- Chrome (Selenium Manager fetches the matching driver)
- A Salesforce test account for the valid login test

## Run

```bash
cd 02_Prompt_Engineering/03_Selenium_Salesforce_Framework
mvn test -Dsf.username=you@example.com -Dsf.password=your-password
```

Surefire runs the suite in `testng.xml`. Passing the credentials on the command line keeps them out of
`config.properties`; never commit real ones there. `target/` holds the compiled output and is gitignored.
