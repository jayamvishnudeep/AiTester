// spec: specs/ttacart-e2e-order-plan.md §2.2 – §2.3, addendum §8.4

import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { FIRST_ITEM, SORT_OPTIONS, TITLES, URLS } from '../testdata/ttacart.data';

type SortValue = (typeof SORT_OPTIONS)[keyof typeof SORT_OPTIONS];

/** The products page reached on a successful login. */
export class InventoryPage extends BasePage {
  readonly url = URLS.inventory;
  readonly title = TITLES.inventory;

  private readonly itemsEl: Locator;
  private readonly itemNamesEl: Locator;
  private readonly itemPricesEl: Locator;
  private readonly sortDropdownEl: Locator;

  constructor(page: Page) {
    super(page, 'InventoryPage');
    this.itemsEl = page.locator('.inventory-item');
    this.itemNamesEl = page.locator('[data-test="inventory-item-name"]');
    this.itemPricesEl = page.locator('[data-test="inventory-item-price"]');
    this.sortDropdownEl = page.locator('#product-sort-container');
  }

  get items(): Locator {
    return this.itemsEl;
  }
  get itemNames(): Locator {
    return this.itemNamesEl;
  }
  get itemPrices(): Locator {
    return this.itemPricesEl;
  }
  get sortDropdown(): Locator {
    return this.sortDropdownEl;
  }

  /**
   * The Add to cart control for a product.
   *
   * On click the button re-renders as Remove and its `data-test` attribute flips
   * with it, so add and remove are two different elements rather than one element
   * changing label (plan §2.3).
   */
  addToCartButton(productId: string = FIRST_ITEM.id): Locator {
    return this.page.locator(`[data-test="add-to-cart-${productId}"]`);
  }

  removeButton(productId: string = FIRST_ITEM.id): Locator {
    return this.page.locator(`[data-test="remove-${productId}"]`);
  }

  // --- actions ---------------------------------------------------------------

  /**
   * Add the first card under the default A-to-Z sort and wait for the badge.
   *
   * The wait matters: the badge is INSERTED into the header rather than revealed,
   * so this is the point at which the DOM settles (plan §6.4).
   */
  async addFirstItemToCart(): Promise<void> {
    this.log.info(`add "${FIRST_ITEM.name}" to the cart`);
    await this.addToCartButton().click();
    await expect(this.cartBadge).toHaveText('1');
  }

  /** Change the sort order. The four verified values are in SORT_OPTIONS. */
  async sortBy(value: SortValue): Promise<void> {
    this.log.info(`sort by "${value}"`);
    await this.sortDropdownEl.selectOption(value);
  }

  // --- assertions ------------------------------------------------------------

  /** Assert the default sort is Name (A to Z) and reads as such. */
  async expectDefaultSort(): Promise<void> {
    await expect(this.sortDropdownEl).toHaveValue(SORT_OPTIONS.nameAsc);
    await expect(
      this.sortDropdownEl.locator(`option[value="${SORT_OPTIONS.nameAsc}"]`),
    ).toHaveText('Name (A to Z)');
  }

  async expectFirstItem(name: string, price?: string): Promise<void> {
    await expect(this.itemNamesEl.first()).toHaveText(name);
    if (price !== undefined) {
      await expect(this.itemPricesEl.first()).toHaveText(price);
    }
  }
}
