// spec: specs/ttacart-e2e-order-plan.md

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { CART_EMPTY_MESSAGE, FIRST_ITEM, TITLES, URLS } from '../fixtures/test-data';

/** The cart page. */
export class CartPage extends BasePage {
  readonly url = URLS.cart;
  readonly title = TITLES.cart;

  readonly lineItems: Locator;
  readonly itemName: Locator;
  readonly itemPrice: Locator;
  readonly itemQuantity: Locator;
  readonly emptyMessage: Locator;

  /**
   * Checkout and Continue Shopping are **anchors**, not buttons (plan §6.5).
   * `getByRole('button')` does not find them, which is why every control here
   * is addressed by its `data-test` attribute.
   */
  readonly checkoutLink: Locator;
  readonly continueShoppingLink: Locator;

  constructor(page: Page) {
    super(page);
    this.lineItems = page.locator('[data-test="inventory-item"]');
    this.itemName = page.locator('[data-test="inventory-item-name"]');
    this.itemPrice = page.locator('[data-test="inventory-item-price"]');
    this.itemQuantity = page.locator('[data-test="item-quantity"]');
    this.emptyMessage = page.locator('[data-test="cart-empty"]');
    this.checkoutLink = page.locator('[data-test="checkout"]');
    this.continueShoppingLink = page.locator('[data-test="continue-shopping"]');
  }

  removeButton(productId: string = FIRST_ITEM.id): Locator {
    return this.page.locator(`[data-test="remove-${productId}"]`);
  }

  async checkout(): Promise<void> {
    await this.checkoutLink.click();
  }

  /** Assert a single line for the given product, at the given price. */
  async expectSingleLineItem(name: string, price: string): Promise<void> {
    await expect(this.lineItems).toHaveCount(1);
    await expect(this.itemName).toHaveText(name);
    await expect(this.itemPrice).toHaveText(price);
    await expect(this.itemQuantity).toHaveText('1');
  }

  async expectEmpty(): Promise<void> {
    await expect(this.emptyMessage).toHaveText(CART_EMPTY_MESSAGE);
    await expect(this.lineItems).toHaveCount(0);
  }
}
