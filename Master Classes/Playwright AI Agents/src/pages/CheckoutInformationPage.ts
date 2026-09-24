// spec: specs/ttacart-e2e-order-plan.md

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { CUSTOMER, TITLES, URLS } from '../fixtures/test-data';

/**
 * Checkout step one — the customer information form.
 *
 * Hazard, plan §6.3: on a successful Continue these three values are written to
 * localStorage under `tta-cart-checkout-info`, this page **pre-fills** from that
 * key on every later visit, and the key is not cleared when an order completes.
 * That is why the test fixture clears site storage before every test; without
 * it the blank-field negatives below submit leftover values and pass while
 * testing nothing.
 */
export class CheckoutInformationPage extends BasePage {
  readonly url = URLS.checkoutStepOne;
  readonly title = TITLES.checkoutStepOne;

  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly postalCodeInput: Locator;

  /** Continue is a real button; Cancel is an anchor (plan §6.5). */
  readonly continueButton: Locator;
  readonly cancelLink: Locator;

  constructor(page: Page) {
    super(page);
    this.firstNameInput = page.locator('#first-name');
    this.lastNameInput = page.locator('#last-name');
    this.postalCodeInput = page.locator('#postal-code');
    this.continueButton = page.locator('[data-test="continue"]');
    this.cancelLink = page.locator('[data-test="cancel"]');
  }

  /**
   * Fill all three fields. An empty string means "leave this one blank", which
   * is exactly what the §4.1–4.3 negatives need.
   */
  async fillDetails(
    firstName: string,
    lastName: string,
    postalCode: string,
  ): Promise<void> {
    await this.firstNameInput.fill(firstName);
    await this.lastNameInput.fill(lastName);
    await this.postalCodeInput.fill(postalCode);
  }

  /** Fill the standard valid details used by every scenario that must get past here. */
  async fillValidDetails(): Promise<void> {
    await this.fillDetails(
      CUSTOMER.firstName,
      CUSTOMER.lastName,
      CUSTOMER.postalCode,
    );
  }

  async continue(): Promise<void> {
    await this.continueButton.click();
  }

  async cancel(): Promise<void> {
    await this.cancelLink.click();
  }

  /**
   * Assert the form starts empty.
   *
   * This holds only from a genuinely clean context — see the storage hazard in
   * the class comment above.
   */
  async expectFieldsEmpty(): Promise<void> {
    await expect(this.firstNameInput).toHaveValue('');
    await expect(this.lastNameInput).toHaveValue('');
    await expect(this.postalCodeInput).toHaveValue('');
  }
}
