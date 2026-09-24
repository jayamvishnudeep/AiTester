// spec: specs/ttacart-e2e-order-plan.md

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { TITLES, URLS } from '../fixtures/test-data';

/**
 * The login page — the application root.
 *
 * Both fields carry the HTML `required` attribute, which is why this class
 * exposes two different ways to submit. See `submit` versus `loginAs`.
 */
export class LoginPage extends BasePage {
  readonly url = URLS.login;
  readonly title = TITLES.login;

  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly loginContainer: Locator;

  constructor(page: Page) {
    super(page);
    this.usernameInput = page.locator('#user-name');
    this.passwordInput = page.locator('#password');
    this.loginButton = page.locator('#login-button');
    this.loginContainer = page.locator('[data-test="login-container"]');
  }

  async fillCredentials(username: string, password: string): Promise<void> {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
  }

  /**
   * Submit the form without asserting the outcome.
   *
   * This is what every negative login scenario uses: the point of those tests
   * is what happens when login does *not* succeed, so asserting success here
   * would make them impossible to write.
   */
  async submit(username: string, password: string): Promise<void> {
    await this.fillCredentials(username, password);
    await this.loginButton.click();
  }

  /**
   * Fill only the password and submit, leaving the username untouched.
   * Used by §3.4, where the empty field must stay genuinely untouched so that
   * Chromium's own `required` check is what blocks the submit.
   */
  async submitWithoutUsername(password: string): Promise<void> {
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }

  /** The mirror of the above for §3.5. */
  async submitWithoutPassword(username: string): Promise<void> {
    await this.usernameInput.fill(username);
    await this.loginButton.click();
  }

  /** Submit and assert the products page was reached. */
  async loginAs(username: string, password: string): Promise<void> {
    await this.submit(username, password);
    await expect(this.page).toHaveURL(URLS.inventory);
  }

  /**
   * Assert a field was blocked by native browser validation.
   *
   * §3.4/§3.5 assert `validity.valueMissing` rather than a banner because the
   * `required` attribute stops the submit before the application ever runs —
   * no request happens, so there is no banner that could exist. Whitespace-only
   * values are a different story and reach the app's own validator (§3.6).
   */
  async expectBlockedByNativeValidation(field: Locator): Promise<void> {
    await expect(field).toHaveJSProperty('validity.valueMissing', true);
  }
}
