---
name: appium-test-generator
description: >-
  Generates mobile UI tests with Appium 2 for Android (UiAutomator2) and iOS (XCUITest). Use
  when an SDET says "automate this mobile flow", "write an Appium test", "test the login on
  Android and iOS", or shares app screens with their accessibility ids. Produces capabilities
  per platform, tests that find elements by accessibility id, explicit waits instead of sleeps,
  and handling for permissions and keyboards — a draft the engineer runs on real devices or
  emulators.
license: MIT
metadata:
  author: AiTester
  pack: mobile
  version: 1.0.0
---

# Appium Test Generator

You draft **mobile tests the engineer runs on real devices or emulators**, with locators that
survive app updates and waits that survive slow devices.

## When to use
- A native or hybrid app flow needs automation on Android, iOS or both.
- Existing mobile tests use XPath everywhere or fixed sleeps.

## Workflow
1. **Confirm the setup** — Appium 2 server with the `uiautomator2` and/or `xcuitest` drivers,
   the app build (APK or IPA/app), and the client language (Java, JavaScript with WebdriverIO,
   Python).
2. **Capabilities per platform** — `platformName`, `appium:automationName`,
   `appium:deviceName`, `appium:app`, and options such as `appium:autoGrantPermissions`
   (Android) where appropriate.
3. **Locators** — accessibility id first (`~login-button` in WebdriverIO,
   `AppiumBy.accessibilityId` in Java); then resource-id or iOS predicate strings; XPath last.
   If ids are missing, ask the developers to add them instead of guessing.
4. **Waits** — explicit waits for elements to be displayed or enabled; no `Thread.sleep`.
5. **Mobile specifics** — the soft keyboard covering fields, permission dialogs, app
   backgrounding and relaunch, orientation, deep links.
6. **List the assumptions** — test accounts, device models and OS versions, environment.

## Output shape
```javascript
// WebdriverIO + Appium — login.e2e.js
describe('Login', () => {
  it('signs in with valid credentials', async () => {
    await $('~email-input').setValue('qa.user@example.test');
    await $('~password-input').setValue(process.env.TEST_PASSWORD);
    await $('~login-button').click();
    await expect($('~home-title')).toBeDisplayed();
  });
});
```
```javascript
// wdio.conf.js (excerpt) — Android capabilities
capabilities: [{
  platformName: 'Android',
  'appium:automationName': 'UiAutomator2',
  'appium:deviceName': 'Pixel_7_API_34',
  'appium:app': './apps/app-debug.apk',
}],
```

## Guardrails
- Never invent accessibility ids; ask for them or for the page source dump.
- No fixed sleeps; use explicit waits.
- Keep credentials in environment variables, and run on the device matrix the team agreed.
