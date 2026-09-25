// spec: specs/ttacart-e2e-order-plan.md §3

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { TITLES, URLS } from '../testdata/ttacart.data';

/**
 * The login page — the application root.
 *
 * Both fields carry the HTML `required` attribute, which is why there are
 * several ways to submit here. See `submit` versus `loginAs`, and the two
 * deliberately-partial submitters below.
 */
export class LoginPage extends BasePage {
  readonly url = URLS.login;
  readonly title = TITLES.login;

  private readonly usernameInputEl: Locator;
  private readonly passwordInputEl: Locator;
  private readonly loginButtonEl: Locator;
  private readonly loginContainerEl: Locator;

  constructor(page: Page) {
    super(page, 'LoginPage');
    this.usernameInputEl = page.locator('#user-name');
    this.passwordInputEl = page.locator('#password');
    this.loginButtonEl = page.locator('#login-button');
    this.loginContainerEl = page.locator('[data-test="login-container"]');
  }

  get usernameInput(): Locator {
    return this.usernameInputEl;
  }
  get passwordInput(): Locator {
    return this.passwordInputEl;
  }
  get loginContainer(): Locator {
    return this.loginContainerEl;
  }

  // --- actions ---------------------------------------------------------------

  async fillCredentials(username: string, password: string): Promise<void> {
    await this.usernameInputEl.fill(username);
    await this.passwordInputEl.fill(password);
  }

  /**
   * Submit without asserting the outcome.
   *
   * What every negative scenario uses: the point of those tests is what happens
   * when login does not succeed, so asserting success here would make them
   * impossible to write.
   */
  async submit(username: string, password: string): Promise<void> {
    this.log.info(`submit login as "${username}"`);
    await this.fillCredentials(username, password);
    await this.loginButtonEl.click();
  }

  /**
   * Fill only the password and submit, leaving the username untouched.
   * §3.4 needs the empty field genuinely untouched so that Chromium's own
   * `required` check is what blocks the submit.
   */
  async submitWithoutUsername(password: string): Promise<void> {
    this.log.info('submit with the username left blank');
    await this.passwordInputEl.fill(password);
    await this.loginButtonEl.click();
  }

  /** The mirror of the above, for §3.5. */
  async submitWithoutPassword(username: string): Promise<void> {
    this.log.info('submit with the password left blank');
    await this.usernameInputEl.fill(username);
    await this.loginButtonEl.click();
  }

  /** Submit and assert the products page was reached. */
  async loginAs(username: string, password: string): Promise<void> {
    await this.submit(username, password);
    await expect(this.page).toHaveURL(URLS.inventory);
  }

  // --- assertions ------------------------------------------------------------

  /**
   * Assert a field was blocked by native browser validation.
   *
   * §3.4/§3.5 assert `validity.valueMissing` rather than a banner because the
   * `required` attribute stops the submit before the application ever runs — no
   * request happens, so there is no banner that could exist. Whitespace-only
   * values are a different story and reach the app's own validator (§3.6).
   */
  async expectBlockedByNativeValidation(field: Locator): Promise<void> {
    await expect(field).toHaveJSProperty('validity.valueMissing', true);
  }
}
