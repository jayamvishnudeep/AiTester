// spec: specs/ttacart-e2e-order-plan.md

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { ORDER_DETAILS, TITLES, URLS } from '../fixtures/test-data';

/** Totals as the overview renders them, label text included. */
export interface OrderTotals {
  readonly subtotal: string;
  readonly tax: string;
  readonly total: string;
}

/** Checkout step two — the order summary. */
export class CheckoutOverviewPage extends BasePage {
  readonly url = URLS.checkoutStepTwo;
  readonly title = TITLES.checkoutStepTwo;

  readonly lineItems: Locator;
  readonly itemName: Locator;
  readonly itemPrice: Locator;
  readonly itemQuantity: Locator;

  readonly paymentValue: Locator;
  readonly shippingValue: Locator;
  readonly subtotalLabel: Locator;
  readonly taxLabel: Locator;
  readonly totalLabel: Locator;

  /** Finish is a real button; Cancel is an anchor (plan §6.5). */
  readonly finishButton: Locator;
  readonly cancelLink: Locator;

  constructor(page: Page) {
    super(page);
    this.lineItems = page.locator('[data-test="inventory-item"]');
    this.itemName = page.locator('[data-test="inventory-item-name"]');
    this.itemPrice = page.locator('[data-test="inventory-item-price"]');
    this.itemQuantity = page.locator('[data-test="item-quantity"]');

    this.paymentValue = page.locator('[data-test="payment-info-value"]');
    this.shippingValue = page.locator('[data-test="shipping-info-value"]');
    this.subtotalLabel = page.locator('[data-test="subtotal-label"]');
    this.taxLabel = page.locator('[data-test="tax-label"]');
    this.totalLabel = page.locator('[data-test="total-label"]');

    this.finishButton = page.locator('[data-test="finish"]');
    this.cancelLink = page.locator('[data-test="cancel"]');
  }

  async finish(): Promise<void> {
    await this.finishButton.click();
  }

  /**
   * Cancel from the overview.
   *
   * TTACart returns to the **cart**, not to the products page as saucedemo.com
   * does — a divergence worth not copying an assertion for (plan §4.6).
   */
  async cancel(): Promise<void> {
    await this.cancelLink.click();
  }

  async expectSingleLineItem(name: string, price: string): Promise<void> {
    await expect(this.lineItems).toHaveCount(1);
    await expect(this.itemName).toHaveText(name);
    await expect(this.itemPrice).toHaveText(price);
    await expect(this.itemQuantity).toHaveText('1');
  }

  async expectTotals(totals: OrderTotals): Promise<void> {
    await expect(this.subtotalLabel).toHaveText(totals.subtotal);
    await expect(this.taxLabel).toHaveText(totals.tax);
    await expect(this.totalLabel).toHaveText(totals.total);
  }

  /** Payment and courier strings are TTACart's own (plan §1.3). */
  async expectPaymentAndShipping(): Promise<void> {
    await expect(this.paymentValue).toHaveText(ORDER_DETAILS.payment);
    await expect(this.shippingValue).toHaveText(ORDER_DETAILS.shipping);
  }
}
