// spec: specs/ttacart-e2e-order-plan.md §2.6, §4.6, addendum §8.7 – §8.9

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { ORDER_DETAILS, TITLES, URLS } from '../testdata/ttacart.data';

/** Totals as the overview renders them, label text included. */
export interface OrderTotals {
  readonly subtotal: string;
  readonly tax: string;
  readonly total: string;
}

/**
 * Checkout step two — the order summary.
 *
 * Two suspected bugs live on this page (addendum §9.1, §9.2): it renders by URL
 * for any signed-in user whether or not step one was completed, and after a
 * completed order it stays in history with a live Finish button, so Back-then-
 * Finish places the order again.
 */
export class CheckoutOverviewPage extends BasePage {
  readonly url = URLS.checkoutStepTwo;
  readonly title = TITLES.checkoutStepTwo;

  private readonly lineItemsEl: Locator;
  private readonly itemNameEl: Locator;
  private readonly itemPriceEl: Locator;
  private readonly itemQuantityEl: Locator;

  private readonly paymentValueEl: Locator;
  private readonly shippingValueEl: Locator;
  private readonly subtotalLabelEl: Locator;
  private readonly taxLabelEl: Locator;
  private readonly totalLabelEl: Locator;

  /** Finish is a real button; Cancel is an anchor (plan §6.5). */
  private readonly finishButtonEl: Locator;
  private readonly cancelLinkEl: Locator;

  constructor(page: Page) {
    super(page, 'CheckoutOverviewPage');
    this.lineItemsEl = page.locator('[data-test="inventory-item"]');
    this.itemNameEl = page.locator('[data-test="inventory-item-name"]');
    this.itemPriceEl = page.locator('[data-test="inventory-item-price"]');
    this.itemQuantityEl = page.locator('[data-test="item-quantity"]');

    this.paymentValueEl = page.locator('[data-test="payment-info-value"]');
    this.shippingValueEl = page.locator('[data-test="shipping-info-value"]');
    this.subtotalLabelEl = page.locator('[data-test="subtotal-label"]');
    this.taxLabelEl = page.locator('[data-test="tax-label"]');
    this.totalLabelEl = page.locator('[data-test="total-label"]');

    this.finishButtonEl = page.locator('[data-test="finish"]');
    this.cancelLinkEl = page.locator('[data-test="cancel"]');
  }

  get lineItems(): Locator {
    return this.lineItemsEl;
  }
  get itemName(): Locator {
    return this.itemNameEl;
  }
  get itemPrice(): Locator {
    return this.itemPriceEl;
  }
  get paymentValue(): Locator {
    return this.paymentValueEl;
  }
  get shippingValue(): Locator {
    return this.shippingValueEl;
  }
  get subtotalLabel(): Locator {
    return this.subtotalLabelEl;
  }
  get taxLabel(): Locator {
    return this.taxLabelEl;
  }
  get totalLabel(): Locator {
    return this.totalLabelEl;
  }
  get finishButton(): Locator {
    return this.finishButtonEl;
  }
  get cancelLink(): Locator {
    return this.cancelLinkEl;
  }

  // --- actions ---------------------------------------------------------------

  async finish(): Promise<void> {
    this.log.info('finish the order');
    await this.finishButtonEl.click();
  }

  /**
   * Cancel from the overview.
   *
   * TTACart returns to the CART, not to the products page as saucedemo.com does —
   * a divergence worth not copying an assertion for (plan §4.6).
   */
  async cancel(): Promise<void> {
    this.log.info('cancel back to the cart');
    await this.cancelLinkEl.click();
  }

  // --- assertions ------------------------------------------------------------

  async expectSingleLineItem(name: string, price: string): Promise<void> {
    await expect(this.lineItemsEl).toHaveCount(1);
    await expect(this.itemNameEl).toHaveText(name);
    await expect(this.itemPriceEl).toHaveText(price);
    await expect(this.itemQuantityEl).toHaveText('1');
  }

  async expectTotals(totals: OrderTotals): Promise<void> {
    await expect(this.subtotalLabelEl).toHaveText(totals.subtotal);
    await expect(this.taxLabelEl).toHaveText(totals.tax);
    await expect(this.totalLabelEl).toHaveText(totals.total);
  }

  /** Payment and courier strings are TTACart's own (plan §1.3). */
  async expectPaymentAndShipping(): Promise<void> {
    await expect(this.paymentValueEl).toHaveText(ORDER_DETAILS.payment);
    await expect(this.shippingValueEl).toHaveText(ORDER_DETAILS.shipping);
  }
}
