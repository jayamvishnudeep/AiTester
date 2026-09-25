// spec: specs/ttacart-e2e-order-plan.md §3
// seed: src/tests/seed.spec.ts
//
// Why these tests are not all shaped the same way.
//
// §3.4/§3.5 assert `validity.valueMissing`; §3.6/§3.7 assert the application's
// own error banners. Side by side that looks inconsistent — it is testing two
// different layers. Both fields carry the HTML `required` attribute, so a
// genuinely empty field is blocked by Chromium before the application runs: no
// request happens, so there is no banner that could exist. A space satisfies
// `required`, so whitespace passes the native check, reaches the app, and
// produces the app's own message. Asserting a banner for the empty case would be
// asserting something that cannot exist.

import { expect, test } from '@fixtures/test-base';
import { accounts, standardUser } from '@config/credentials';
import { ERRORS, TITLES, URLS, WHITESPACE } from '@testdata/ttacart.data';

test.describe('Login — negative', () => {
  // ------------------------------------------------------------------- §3.1
  test('Invalid password is refused @p0', async ({ page, loginPage }) => {
    // 1-4. On the login page, the valid username with a wrong password.
    await loginPage.submit(standardUser.username, 'wrong_password');

    await loginPage.expectAtUrl();
    await loginPage.expectError(ERRORS.credentials);
    await expect(loginPage.errorBanner).toHaveAttribute('role', 'alert');

    // No session: the products page is still unreachable by deep link.
    await page.goto(URLS.inventory);
    await loginPage.expectAtUrl();
  });

  // ------------------------------------------------------------------- §3.2
  test('Locked-out user cannot log in', async ({ page, loginPage }) => {
    await loginPage.submit(accounts.lockedOut, standardUser.password);

    await loginPage.expectAtUrl();
    await loginPage.expectError(ERRORS.lockedOut);

    // No session was written, so the products page cannot be deep-linked.
    await page.goto(URLS.inventory);
    await loginPage.expectLoaded();
  });

  // ------------------------------------------------------------------- §3.3
  test('Unknown username gets the same message as a bad password', async ({
    loginPage,
  }) => {
    await loginPage.submit(accounts.unknown, standardUser.password);

    await loginPage.expectAtUrl();
    // Identical to §3.1 — the app does not distinguish the two cases, which is
    // the correct behaviour: telling them apart enumerates valid usernames.
    await loginPage.expectError(ERRORS.credentials);
  });

  // ------------------------------------------------------------------- §3.4
  test('Empty username is blocked by native browser validation', async ({
    loginPage,
  }) => {
    // Leave the username blank, enter the password, click Login.
    await loginPage.submitWithoutUsername(standardUser.password);

    // The submit never reaches the application, so assert valueMissing rather
    // than a banner — the app's own "Username is required" branch is unreachable
    // this way. §3.6 is the only route to it.
    await loginPage.expectBlockedByNativeValidation(loginPage.usernameInput);
    await loginPage.expectNoError();
    await loginPage.expectAtUrl();
  });

  // ------------------------------------------------------------------- §3.5
  test('Empty password is blocked by native browser validation', async ({
    loginPage,
  }) => {
    await loginPage.submitWithoutPassword(standardUser.username);

    await loginPage.expectBlockedByNativeValidation(loginPage.passwordInput);
    await loginPage.expectNoError();
    await loginPage.expectAtUrl();
  });

  // ------------------------------------------------------------------- §3.6
  test('Whitespace-only username reports that the username is required', async ({
    loginPage,
  }) => {
    // Three spaces satisfy native validation, so the app's own validator runs
    // and trims the value. This is the only route to this message.
    await loginPage.submit(WHITESPACE, standardUser.password);

    await loginPage.expectAtUrl();
    await loginPage.expectError(ERRORS.usernameRequired);
  });

  // ------------------------------------------------------------------- §3.7
  test('Whitespace-only password is treated as a wrong password', async ({
    loginPage,
  }) => {
    // The password is not trimmed, so spaces are a genuine wrong password.
    await loginPage.submit(standardUser.username, WHITESPACE);

    await loginPage.expectAtUrl();
    // Not a "required" message.
    await loginPage.expectError(ERRORS.credentials);
    await expect(loginPage.passwordInput).toHaveValue(WHITESPACE);
  });

  // ------------------------------------------------------------------- §3.8
  test('Username matching is case-sensitive', async ({ loginPage }) => {
    await loginPage.submit(accounts.wrongCase, standardUser.password);

    await loginPage.expectAtUrl();
    await loginPage.expectError(ERRORS.credentials);
  });

  // ------------------------------------------------------------------- §3.9
  test('Checkout pages are not reachable while logged out @p0', async ({
    page,
    loginPage,
  }) => {
    // The cleanSession fixture cleared storage, so no session exists.
    await page.goto(URLS.checkoutStepOne);
    await loginPage.expectLoaded();
    await expect(loginPage.loginContainer).toBeVisible();

    // The same guard protects every other step of the order flow.
    for (const guarded of [
      URLS.inventory,
      URLS.cart,
      URLS.checkoutStepTwo,
      URLS.checkoutComplete,
    ]) {
      await page.goto(guarded);
      await expect(page).toHaveURL(URLS.login);
      await expect(page).toHaveTitle(TITLES.login);
    }
  });
});
