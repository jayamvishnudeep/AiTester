// spec: specs/ttacart-e2e-order-plan.md

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { CONFIRMATION, TITLES, URLS } from '../fixtures/test-data';

/** The confirmation page reached by clicking Finish. */
export class CheckoutCompletePage extends BasePage {
  readonly url = URLS.checkoutComplete;
  readonly title = TITLES.checkoutComplete;

  readonly container: Locator;
  readonly header: Locator;
  readonly text: Locator;
  readonly ponyExpress: Locator;
  readonly backHomeButton: Locator;

  constructor(page: Page) {
    super(page);
    this.container = page.locator('[data-test="checkout-complete-container"]');
    this.header = page.locator('[data-test="complete-header"]');
    this.text = page.locator('[data-test="complete-text"]');
    this.ponyExpress = page.locator('[data-test="pony-express"]');
    this.backHomeButton = page.locator('[data-test="back-to-products"]');
  }

  /** The confirmation headline and body copy, verbatim. */
  async expectOrderConfirmed(): Promise<void> {
    await expect(this.header).toHaveText(CONFIRMATION.header);
    await expect(this.text).toHaveText(CONFIRMATION.text);
    await expect(this.backHomeButton).toHaveText(CONFIRMATION.backHome);
  }

  /** Just the headline — for scenarios where reaching confirmation is the point. */
  async expectConfirmationHeader(): Promise<void> {
    await expect(this.header).toHaveText(CONFIRMATION.header);
  }
}
