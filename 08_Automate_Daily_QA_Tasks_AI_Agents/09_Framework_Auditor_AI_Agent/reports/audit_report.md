# Framework audit — sample_framework_java

*Generated 2026-09-16 by the Framework Auditor. Every count below is measured, not estimated — re-run the scanner to reproduce it.*

## At a glance

| | |
|---|---|
| Repository | `e:\Visual Studio Code\AiTester\08_Automate_Daily_QA_Tasks_AI_Agents\09_Framework_Auditor_AI_Agent\sample_framework_java` |
| Files scanned | 4 (4 java) |
| Lines scanned | 209 |
| Findings | **65** — 26 high, 37 medium, 2 low |
| Dependencies behind | 7 of 8 |

## What was found

| Severity | Anti-pattern | Occurrences | Files |
|---|---|---:|---:|
| HIGH | Hard-coded sleep | 15 | 4 |
| HIGH | Absolute XPath | 5 | 3 |
| HIGH | Static mutable driver | 3 | 3 |
| HIGH | Assertion inside a page object | 2 | 1 |
| HIGH | Credential in source | 1 | 1 |
| MEDIUM | WebDriver call in the test layer | 15 | 2 |
| MEDIUM | Index-based XPath | 6 | 3 |
| MEDIUM | Selector tied to styling | 6 | 3 |
| MEDIUM | Environment URL in source | 5 | 3 |
| MEDIUM | Implicit wait | 3 | 3 |
| MEDIUM | Disabled test | 2 | 1 |
| LOW | Console output instead of logging | 2 | 1 |

## Dependencies behind the current line

| Package | Pinned at | Why it matters |
|---|---|---|
| `selenium-java` | `3.141.59` | Selenium 4 has been current since 2021; 3.x predates the W3C WebDriver protocol and bundled Selenium Manager |
| `testng` | `6.14.3` | TestNG 7 has been current since 2019 and is required for recent JDKs |
| `junit` | `4.12` | JUnit 4 is in maintenance only; JUnit 5 is the current platform |
| `webdrivermanager` | `4.4.3` | Selenium 4.6 manages drivers itself, so this may not be needed at all any more |
| `commons-lang3` | `3.9` | commons-lang3 3.9 is from 2019 |
| `maven-surefire-plugin` | `2.22.2` | Surefire 3 is required for JUnit 5 and recent JDKs |
| `maven.compiler.target` | `8` | Java 17 and 21 are the current LTS releases |

---

## Recommendations

*This section is written by a language model from the evidence above. The counts are not its work; the priorities are.*

The framework is structurally unsound, with 65 findings indicating a brittle, non-scalable foundation. The single biggest problem is the **static mutable driver** in `DriverFactory.java:10` and `CheckoutTest.java:14`. This architectural flaw serializes the entire suite, preventing parallel execution and causing state leakage between tests, which caps throughput and introduces unpredictable flakiness that no amount of waiting can fix.

**Fix first**
1.  **Replace static drivers with instance-scoped drivers.** Refactor `DriverFactory.java:10` and `CheckoutTest.java:14` to use `@BeforeMethod`/`@AfterMethod` or TestNG `@Factory` to instantiate a fresh `WebDriver` per test. This is a medium-sized refactor (approx. 1-2 days) that removes the primary blocker to parallelization, potentially reducing total suite runtime by 50-70% and eliminating cross-test state pollution.
2.  **Eliminate hard-coded sleeps.** Replace the 15 occurrences of `Thread.sleep` (e.g., `LoginPage.java:18`, `CheckoutTest.java:25`) with explicit `WebDriverWait` conditions. This is a low-effort task (approx. 1 day) that directly reduces execution time by removing unnecessary waits (e.g., the 4000ms wait in `CheckoutTest.java:25`) and increases reliability by waiting for actual state changes rather than arbitrary time.
3.  **Move assertions out of page objects.** Remove `Assert` calls from `LoginPage.java:36` and `LoginPage.java:42`. This is a small change (approx. 4 hours) that restores the Single Responsibility Principle, allowing page objects to be reused for negative testing and making test intent explicit in the test layer.

**Then**
*   Replace absolute XPaths (e.g., `LoginPage.java:22`) with stable CSS selectors or data attributes to reduce maintenance overhead.
*   Externalize environment URLs and credentials (e.g., `pom.xml` dependencies, source code) to configuration files to enable multi-environment testing and security compliance.
*   Upgrade Selenium to 4.x in `pom.xml` to leverage W3C protocol improvements and remove the need for `webdrivermanager`.

**Leave for now**
*   **Disabled tests:** While 2 disabled tests represent lost coverage, re-enabling them requires investigating the original failure cause, which is higher effort than the immediate structural fixes above.
*   **Console output:** Replacing `System.out` with a logging framework is low priority as it does not impact test stability or execution speed, only observability.

---

## Appendix — every occurrence (65)

### Hard-coded sleep — 15 [high]

- `src/main/java/com/shopfront/pages/LoginPage.java:18` — `Thread.sleep(2000);`
- `src/main/java/com/shopfront/pages/LoginPage.java:31` — `Thread.sleep(3000);`
- `src/main/java/com/shopfront/utils/DriverFactory.java:22` — `Thread.sleep(millis);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:25` — `Thread.sleep(4000);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:28` — `Thread.sleep(4000);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:33` — `Thread.sleep(8000);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:42` — `Thread.sleep(4000);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:44` — `Thread.sleep(3000);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:53` — `Thread.sleep(4000);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:56` — `Thread.sleep(2000);`
- `src/test/java/com/shopfront/tests/LoginTest.java:32` — `Thread.sleep(3000);`
- `src/test/java/com/shopfront/tests/LoginTest.java:38` — `Thread.sleep(5000);`
- `src/test/java/com/shopfront/tests/LoginTest.java:47` — `Thread.sleep(3000);`
- `src/test/java/com/shopfront/tests/LoginTest.java:53` — `Thread.sleep(2000);`
- `src/test/java/com/shopfront/tests/LoginTest.java:62` — `Thread.sleep(3000);`

### Absolute XPath — 5 [high]

- `src/main/java/com/shopfront/pages/LoginPage.java:22` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/div[1]/input")).sendKeys(email);`
- `src/main/java/com/shopfront/pages/LoginPage.java:26` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/div[2]/input")).sendKeys(password);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:27` — `driver.findElement(By.xpath("/html/body/div[1]/main/section[3]/button")).click();`
- `src/test/java/com/shopfront/tests/LoginTest.java:36` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/button")).click();`
- `src/test/java/com/shopfront/tests/LoginTest.java:51` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/button")).click();`

### Static mutable driver — 3 [high]

- `src/main/java/com/shopfront/utils/DriverFactory.java:10` — `public static WebDriver driver;`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:14` — `public static WebDriver driver;`
- `src/test/java/com/shopfront/tests/LoginTest.java:15` — `public static WebDriver driver;`

### Assertion inside a page object — 2 [high]

- `src/main/java/com/shopfront/pages/LoginPage.java:36` — `Assert.assertTrue(driver.getCurrentUrl().contains("dashboard"),`
- `src/main/java/com/shopfront/pages/LoginPage.java:42` — `Assert.assertEquals(actual, expected);`

### Credential in source — 1 [high]

- `src/test/java/com/shopfront/tests/LoginTest.java:19` — `private static final String PASSWORD = "Passw0rd123";`

### WebDriver call in the test layer — 15 [medium]

- `src/test/java/com/shopfront/tests/CheckoutTest.java:27` — `driver.findElement(By.xpath("/html/body/div[1]/main/section[3]/button")).click();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:30` — `driver.findElement(By.xpath("//*[@id=\"root\"]/div/div[2]/div[1]/label[1]/input")).click();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:31` — `driver.findElement(By.cssSelector("button.btn.btn--primary")).click();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:43` — `driver.findElement(By.cssSelector("button.btn.btn--primary")).click();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:46` — `driver.findElement(By.cssSelector("div.checkout__error")).getText(),`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:54` — `driver.findElement(By.id("promo")).sendKeys("APRON10");`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:55` — `driver.findElement(By.cssSelector("button.btn.btn--ghost")).click();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:57` — `Assert.assertEquals(driver.findElement(By.cssSelector("dd.total")).getText(), "£21.60");`
- `src/test/java/com/shopfront/tests/LoginTest.java:34` — `driver.findElement(By.id("email")).sendKeys(USERNAME);`
- `src/test/java/com/shopfront/tests/LoginTest.java:35` — `driver.findElement(By.id("password")).sendKeys(PASSWORD);`
- `src/test/java/com/shopfront/tests/LoginTest.java:36` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/button")).click();`
- `src/test/java/com/shopfront/tests/LoginTest.java:49` — `driver.findElement(By.id("email")).sendKeys(USERNAME);`
- `src/test/java/com/shopfront/tests/LoginTest.java:50` — `driver.findElement(By.id("password")).sendKeys("not-the-password");`
- `src/test/java/com/shopfront/tests/LoginTest.java:51` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/button")).click();`
- `src/test/java/com/shopfront/tests/LoginTest.java:55` — `String error = driver.findElement(By.cssSelector("div.auth__error > span.text-red-500")).getText();`

### Index-based XPath — 6 [medium]

- `src/main/java/com/shopfront/pages/LoginPage.java:22` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/div[1]/input")).sendKeys(email);`
- `src/main/java/com/shopfront/pages/LoginPage.java:26` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/div[2]/input")).sendKeys(password);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:27` — `driver.findElement(By.xpath("/html/body/div[1]/main/section[3]/button")).click();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:30` — `driver.findElement(By.xpath("//*[@id=\"root\"]/div/div[2]/div[1]/label[1]/input")).click();`
- `src/test/java/com/shopfront/tests/LoginTest.java:36` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/button")).click();`
- `src/test/java/com/shopfront/tests/LoginTest.java:51` — `driver.findElement(By.xpath("/html/body/div[1]/main/form/button")).click();`

### Selector tied to styling — 6 [medium]

- `src/main/java/com/shopfront/pages/LoginPage.java:30` — `driver.findElement(By.cssSelector("button.btn.btn--primary")).click();`
- `src/main/java/com/shopfront/pages/LoginPage.java:41` — `String actual = driver.findElement(By.cssSelector("div.auth__error > span.text-red-500")).getText();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:31` — `driver.findElement(By.cssSelector("button.btn.btn--primary")).click();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:43` — `driver.findElement(By.cssSelector("button.btn.btn--primary")).click();`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:55` — `driver.findElement(By.cssSelector("button.btn.btn--ghost")).click();`
- `src/test/java/com/shopfront/tests/LoginTest.java:55` — `String error = driver.findElement(By.cssSelector("div.auth__error > span.text-red-500")).getText();`

### Environment URL in source — 5 [medium]

- `src/main/java/com/shopfront/pages/LoginPage.java:17` — `driver.get("https://shopfront.example.com/login");`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:24` — `driver.get("https://shopfront.example.com/cart");`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:41` — `driver.get("https://shopfront.example.com/checkout");`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:52` — `driver.get("https://shopfront.example.com/checkout");`
- `src/test/java/com/shopfront/tests/LoginTest.java:17` — `private static final String BASE_URL = "https://shopfront.example.com";`

### Implicit wait — 3 [medium]

- `src/main/java/com/shopfront/utils/DriverFactory.java:15` — `driver.manage().timeouts().implicitlyWait(30, java.util.concurrent.TimeUnit.SECONDS);`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:19` — `driver.manage().timeouts().implicitlyWait(30, java.util.concurrent.TimeUnit.SECONDS);`
- `src/test/java/com/shopfront/tests/LoginTest.java:26` — `driver.manage().timeouts().implicitlyWait(30, java.util.concurrent.TimeUnit.SECONDS);`

### Disabled test — 2 [medium]

- `src/test/java/com/shopfront/tests/CheckoutTest.java:38` — `@Ignore`
- `src/test/java/com/shopfront/tests/CheckoutTest.java:50` — `@Test(enabled = false)`

### Console output instead of logging — 2 [low]

- `src/test/java/com/shopfront/tests/LoginTest.java:40` — `System.out.println("Logged in, current url is " + driver.getCurrentUrl());`
- `src/test/java/com/shopfront/tests/LoginTest.java:64` — `System.out.println("checked the button");`
