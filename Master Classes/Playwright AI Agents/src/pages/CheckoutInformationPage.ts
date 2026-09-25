// spec: specs/ttacart-e2e-order-plan.md §2.5, §4.1 – §4.4

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { CUSTOMER, TITLES, URLS } from '../testdata/ttacart.data';

/**
 * Checkout step one — the customer information form.
 *
 * Hazard, plan §6.3: on a successful Continue these three values are written to
 * localStorage under `tta-cart-checkout-info`, this page PRE-FILLS from that key
 * on every later visit, and the key is not cleared when an order completes. The
 * `cleanSession` fixture resets storage before every test for exactly this
 * reason; without it the blank-field negatives arrive at a populated form.
 *
 * Note also addendum §9.2: this form validates correctly, but it is OPTIONAL —
 * checkout step two renders by URL whether or not this page was ever visited.
 */
export class CheckoutInformationPage extends BasePage {
  readonly url = URLS.checkoutStepOne;
  readonly title = TITLES.checkoutStepOne;

  private readonly firstNameInputEl: Locator;
  private readonly lastNameInputEl: Locator;
  private readonly postalCodeInputEl: Locator;

  /** Continue is a real button; Cancel is an anchor (plan §6.5). */
  private readonly continueButtonEl: Locator;
  private readonly cancelLinkEl: Locator;

  constructor(page: Page) {
    super(page, 'CheckoutInformationPage');
    this.firstNameInputEl = page.locator('#first-name');
    this.lastNameInputEl = page.locator('#last-name');
    this.postalCodeInputEl = page.locator('#postal-code');
    this.continueButtonEl = page.locator('[data-test="continue"]');
    this.cancelLinkEl = page.locator('[data-test="cancel"]');
  }

  get firstNameInput(): Locator {
    return this.firstNameInputEl;
  }
  get lastNameInput(): Locator {
    return this.lastNameInputEl;
  }
  get postalCodeInput(): Locator {
    return this.postalCodeInputEl;
  }
  get continueButton(): Locator {
    return this.continueButtonEl;
  }
  get cancelLink(): Locator {
    return this.cancelLinkEl;
  }

  // --- actions ---------------------------------------------------------------

  /**
   * Fill all three fields. An empty string means "leave this one blank", which is
   * exactly what the §4.1 – §4.3 negatives need.
   */
  async fillDetails(
    firstName: string,
    lastName: string,
    postalCode: string,
  ): Promise<void> {
    await this.firstNameInputEl.fill(firstName);
    await this.lastNameInputEl.fill(lastName);
    await this.postalCodeInputEl.fill(postalCode);
  }

  /** The standard valid details, for every scenario that must get past here. */
  async fillValidDetails(): Promise<void> {
    await this.fillDetails(
      CUSTOMER.firstName,
      CUSTOMER.lastName,
      CUSTOMER.postalCode,
    );
  }

  async continue(): Promise<void> {
    this.log.info('continue to the overview');
    await this.continueButtonEl.click();
  }

  async cancel(): Promise<void> {
    this.log.info('cancel back to the cart');
    await this.cancelLinkEl.click();
  }

  // --- assertions ------------------------------------------------------------

  /**
   * Assert the form starts empty. Holds only from a genuinely clean context —
   * see the storage hazard in the class comment.
   */
  async expectFieldsEmpty(): Promise<void> {
    await expect(this.firstNameInputEl).toHaveValue('');
    await expect(this.lastNameInputEl).toHaveValue('');
    await expect(this.postalCodeInputEl).toHaveValue('');
  }
}
