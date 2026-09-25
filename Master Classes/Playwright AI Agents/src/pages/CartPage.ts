// spec: specs/ttacart-e2e-order-plan.md §2.4, §4.5, addendum §8.1 – §8.2

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import {
  CART_EMPTY_MESSAGE,
  FIRST_ITEM,
  TITLES,
  URLS,
} from '../testdata/ttacart.data';

/** The cart page. */
export class CartPage extends BasePage {
  readonly url = URLS.cart;
  readonly title = TITLES.cart;

  private readonly lineItemsEl: Locator;
  private readonly itemNameEl: Locator;
  private readonly itemPriceEl: Locator;
  private readonly itemQuantityEl: Locator;
  private readonly emptyMessageEl: Locator;

  /**
   * Checkout and Continue Shopping are ANCHORS, not buttons (plan §6.5).
   * getByRole('button') does not find them, which is why every control here is
   * addressed by its `data-test` attribute — stable across all six pages.
   */
  private readonly checkoutLinkEl: Locator;
  private readonly continueShoppingLinkEl: Locator;

  constructor(page: Page) {
    super(page, 'CartPage');
    this.lineItemsEl = page.locator('[data-test="inventory-item"]');
    this.itemNameEl = page.locator('[data-test="inventory-item-name"]');
    this.itemPriceEl = page.locator('[data-test="inventory-item-price"]');
    this.itemQuantityEl = page.locator('[data-test="item-quantity"]');
    this.emptyMessageEl = page.locator('[data-test="cart-empty"]');
    this.checkoutLinkEl = page.locator('[data-test="checkout"]');
    this.continueShoppingLinkEl = page.locator('[data-test="continue-shopping"]');
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
  get itemQuantity(): Locator {
    return this.itemQuantityEl;
  }
  get emptyMessage(): Locator {
    return this.emptyMessageEl;
  }
  get checkoutLink(): Locator {
    return this.checkoutLinkEl;
  }
  get continueShoppingLink(): Locator {
    return this.continueShoppingLinkEl;
  }

  removeButton(productId: string = FIRST_ITEM.id): Locator {
    return this.page.locator(`[data-test="remove-${productId}"]`);
  }

  // --- actions ---------------------------------------------------------------

  async checkout(): Promise<void> {
    this.log.info('checkout');
    await this.checkoutLinkEl.click();
  }

  async continueShopping(): Promise<void> {
    this.log.info('continue shopping');
    await this.continueShoppingLinkEl.click();
  }

  async removeFirstItem(): Promise<void> {
    this.log.info(`remove "${FIRST_ITEM.name}"`);
    await this.removeButton().click();
  }

  // --- assertions ------------------------------------------------------------

  async expectSingleLineItem(name: string, price: string): Promise<void> {
    await expect(this.lineItemsEl).toHaveCount(1);
    await expect(this.itemNameEl).toHaveText(name);
    await expect(this.itemPriceEl).toHaveText(price);
    await expect(this.itemQuantityEl).toHaveText('1');
  }

  async expectEmpty(): Promise<void> {
    await expect(this.emptyMessageEl).toHaveText(CART_EMPTY_MESSAGE);
    await expect(this.lineItemsEl).toHaveCount(0);
  }
}
