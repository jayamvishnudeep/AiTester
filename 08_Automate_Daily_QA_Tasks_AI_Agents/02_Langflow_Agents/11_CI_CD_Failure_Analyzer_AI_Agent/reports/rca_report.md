# CI failure analysis — Jenkins

*Generated 2026-09-19 by the Smart CI/CD Failure Analyzer. Every count and every quoted line below is read from the log - re-run the extractor to reproduce it.*

## At a glance

| | |
|---|---|
| CI system | Jenkins |
| Failed step | Build |
| Exit code | 1 |
| Log length | 205 lines |
| Read by the model | 17 lines (92% of the log discarded as noise) |
| Failures | **12** in 4 distinct group(s) |
| Tests | 25 run, **12 failed**, 11 passed, 2 skipped |

## What failed

| Severity | Category | Occurrences | First seen |
|---|---|---:|---:|
| HIGH | Unhandled exception | 9 | line 102 |
| MEDIUM | Assertion failure | 1 | line 165 |
| MEDIUM | Assertion failure | 1 | line 170 |
| MEDIUM | Timeout | 1 | line 175 |

## The evidence

Quoted from the log, with the line each group was first seen at.

### 1. Unhandled exception — 9 occurrences

First at line 102:

```
java.lang.NullPointerException: Cannot invoke "java.lang.String.replace(java.lang.CharSequence, java.lang.CharSequence)" because the return value of "com.shopfront.pages.CheckoutPage.getTotalText()" is null
at com.shopfront.pages.CheckoutPage.getTotal(CheckoutPage.java:88)
at com.shopfront.tests.CheckoutTest.checkoutWithSavedCard(CheckoutTest.java:42)
at java.base/jdk.internal.reflect.DirectMethodHandleAccessor.invoke(DirectMethodHandleAccessor.java:103)
at org.testng.internal.invokers.MethodInvocationHelper.invokeMethod(MethodInvocationHelper.java:139)
at org.testng.internal.invokers.TestInvoker.invokeMethod(TestInvoker.java:677)
```

Also at line 109, line 116 and elsewhere.

### 2. Assertion failure — 1 occurrence

First at line 165:

```
java.lang.AssertionError: expected [Card expired] but found [Payment declined]
at org.testng.Assert.fail(Assert.java:110)
at org.testng.Assert.assertEquals(Assert.java:141)
at com.shopfront.tests.CheckoutTest.checkoutRejectsExpiredCard(CheckoutTest.java:151)
```

### 3. Assertion failure — 1 occurrence

First at line 170:

```
java.lang.AssertionError: expected [2 items] but found [3 items]
at org.testng.Assert.fail(Assert.java:110)
at org.testng.Assert.assertEquals(Assert.java:141)
at com.shopfront.tests.CheckoutTest.checkoutHandlesOutOfStock(CheckoutTest.java:168)
```

### 4. Timeout — 1 occurrence

First at line 175:

```
org.openqa.selenium.TimeoutException: Expected condition failed: waiting for visibility of element located by By.cssSelector: [data-testid='order-confirmation'] (tried for 30 second(s) with 500 milliseconds interval)
at org.openqa.selenium.support.ui.WebDriverWait.timeoutException(WebDriverWait.java:96)
at com.shopfront.tests.CheckoutTest.checkoutUnderLoad(CheckoutTest.java:184)
```

---

## Root cause analysis

*This section is written by a language model from the evidence above. The counts and the grouping are not its work; the explanation is.*

**Why it failed**
The build broke because `CheckoutPage.getTotalText()` returned null, causing a `NullPointerException` in `getTotal()`. This single defect cascaded into 9 of the 12 test failures. The remaining three failures are distinct issues: one assertion mismatch on error messaging, one assertion mismatch on item counts, and one UI timeout.

**The evidence**
The primary failure is the `NullPointerException` at `CheckoutPage.java:88`, triggered by `CheckoutTest.checkoutWithSavedCard` (line 42). The log shows this exception occurring 9 times, starting at line 102. The other failures are isolated: an `AssertionError` at `CheckoutTest.java:151` expecting "Card expired" but finding "Payment declined", another at `CheckoutTest.java:168` expecting "2 items" but finding "3 items", and a `TimeoutException` at `CheckoutTest.java:184` waiting for the order confirmation element.

**What to check first**
1. Inspect `CheckoutPage.getTotalText()` to determine why it returns null; add a null check or fix the underlying data retrieval logic.
2. Verify the backend logic for expired card handling to ensure the correct error message ("Card expired") is returned instead of "Payment declined".
3. Review the inventory logic in `checkoutHandlesOutOfStock` to confirm why the item count is 3 instead of 2.

**Probably unrelated**
The timeout in `checkoutUnderLoad` is likely a separate performance or flakiness issue, distinct from the code defects causing the other failures.
