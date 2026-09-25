// spec: specs/ttacart-e2e-order-plan.md

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { FIRST_ITEM, TITLES, URLS } from '../fixtures/test-data';

/** The products page reached on a successful login. */
export class InventoryPage extends BasePage {
  readonly url = URLS.inventory;
  readonly title = TITLES.inventory;

  readonly items: Locator;
  readonly itemNames: Locator;
  readonly itemPrices: Locator;
  readonly sortDropdown: Locator;

  constructor(page: Page) {
    super(page);
    this.items = page.locator('.inventory-item');
    this.itemNames = page.locator('[data-test="inventory-item-name"]');
    this.itemPrices = page.locator('[data-test="inventory-item-price"]');
    this.sortDropdown = page.locator('#product-sort-container');
  }

  /**
   * The Add to cart control for a product.
   *
   * On click the button re-renders as Remove and its `data-test` attribute
   * flips with it, so the add and remove locators are two different elements
   * rather than one element changing label (plan §2.3).
   */
  addToCartButton(productId: string = FIRST_ITEM.id): Locator {
    return this.page.locator(`[data-test="add-to-cart-${productId}"]`);
  }

  removeButton(productId: string = FIRST_ITEM.id): Locator {
    return this.page.locator(`[data-test="remove-${productId}"]`);
  }

  /**
   * Add the first card under the default A-to-Z sort and wait for the badge.
   *
   * The wait matters: the badge is *inserted* into the header rather than
   * revealed, so this is the point at which the DOM settles (plan §6.4).
   */
  async addFirstItemToCart(): Promise<void> {
    await this.addToCartButton().click();
    await expect(this.cartBadge).toHaveText('1');
  }

  /**
   * Change the sort order. The four verified values are `az`, `za`, `lohi` and
   * `hilo` (plan addendum §8.4).
   */
  async sortBy(value: 'az' | 'za' | 'lohi' | 'hilo'): Promise<void> {
    await this.sortDropdown.selectOption(value);
  }

  /** Assert the default sort is Name (A to Z) and reads as such. */
  async expectDefaultSort(): Promise<void> {
    await expect(this.sortDropdown).toHaveValue('az');
    await expect(this.sortDropdown.locator('option[value="az"]')).toHaveText(
      'Name (A to Z)',
    );
  }
}
