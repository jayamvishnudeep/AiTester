// spec: specs/ttacart-e2e-order-plan.md §2.7, addendum §8.3

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { CONFIRMATION, TITLES, URLS } from '../testdata/ttacart.data';

/** The confirmation page reached by clicking Finish. */
export class CheckoutCompletePage extends BasePage {
  readonly url = URLS.checkoutComplete;
  readonly title = TITLES.checkoutComplete;

  private readonly containerEl: Locator;
  private readonly headerEl: Locator;
  private readonly textEl: Locator;
  private readonly ponyExpressEl: Locator;
  private readonly backHomeButtonEl: Locator;

  constructor(page: Page) {
    super(page, 'CheckoutCompletePage');
    this.containerEl = page.locator('[data-test="checkout-complete-container"]');
    this.headerEl = page.locator('[data-test="complete-header"]');
    this.textEl = page.locator('[data-test="complete-text"]');
    this.ponyExpressEl = page.locator('[data-test="pony-express"]');
    this.backHomeButtonEl = page.locator('[data-test="back-to-products"]');
  }

  get container(): Locator {
    return this.containerEl;
  }
  get header(): Locator {
    return this.headerEl;
  }
  get text(): Locator {
    return this.textEl;
  }
  get ponyExpress(): Locator {
    return this.ponyExpressEl;
  }
  get backHomeButton(): Locator {
    return this.backHomeButtonEl;
  }

  // --- actions ---------------------------------------------------------------

  async backHome(): Promise<void> {
    this.log.info('back home to the products page');
    await this.backHomeButtonEl.click();
  }

  // --- assertions ------------------------------------------------------------

  /** The confirmation headline and body copy, verbatim. */
  async expectOrderConfirmed(): Promise<void> {
    await expect(this.headerEl).toHaveText(CONFIRMATION.header);
    await expect(this.textEl).toHaveText(CONFIRMATION.text);
    await expect(this.backHomeButtonEl).toHaveText(CONFIRMATION.backHome);
  }

  /** Just the headline — where reaching confirmation is the point. */
  async expectConfirmationHeader(): Promise<void> {
    await expect(this.headerEl).toHaveText(CONFIRMATION.header);
  }
}
