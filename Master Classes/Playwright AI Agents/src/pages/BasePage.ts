// spec: specs/ttacart-e2e-order-plan.md

import { expect, type Locator, type Page } from '@playwright/test';

/**
 * Shared behaviour for every TTACart page.
 *
 * The header shell (`[data-test="primary-header"]`, the burger menu, the cart
 * link and its badge) is rendered on all five signed-in pages, and the error
 * banner at `[data-test="error"]` is reused by both the login page and checkout
 * step one — so both live here rather than being redeclared six times.
 *
 * On assertions in page objects: the `expect*` helpers below are deliberately
 * limited to page *identity* and *shell state* — "am I on the right page", "is
 * the badge showing what I think". Everything scenario-specific stays in the
 * spec files, where a reader can see what the test actually claims.
 */
export abstract class BasePage {
  readonly page: Page;

  /** The URL the browser reports for this page, extension-less (plan §1.1). */
  abstract readonly url: string;
  /** `document.title` for this page. */
  abstract readonly title: string;

  // --- the signed-in shell (plan §1.2) ---------------------------------------
  readonly primaryHeader: Locator;
  readonly burgerMenu: Locator;
  readonly cartLink: Locator;
  readonly cartBadge: Locator;
  readonly pageHeading: Locator;
  readonly errorBanner: Locator;

  protected constructor(page: Page) {
    this.page = page;
    this.primaryHeader = page.locator('[data-test="primary-header"]');
    this.burgerMenu = page.locator('[data-test="open-menu"]');
    this.cartLink = page.locator('[data-test="shopping-cart-link"]');
    this.cartBadge = page.locator('[data-test="shopping-cart-badge"]');
    this.pageHeading = page.locator('[data-test="title"]');
    this.errorBanner = page.locator('[data-test="error"]');
  }

  /** Navigate straight to this page. Also the way §3.9 probes the route guard. */
  async goto(): Promise<void> {
    await this.page.goto(this.url);
  }

  /** Assert the browser is on this page, by both URL and document title. */
  async expectLoaded(): Promise<void> {
    await expect(this.page).toHaveURL(this.url);
    await expect(this.page).toHaveTitle(this.title);
  }

  /** Assert the URL only — for steps where the title is not the point. */
  async expectAtUrl(): Promise<void> {
    await expect(this.page).toHaveURL(this.url);
  }

  async openCart(): Promise<void> {
    await this.cartLink.click();
  }

  async expectCartBadgeCount(count: string): Promise<void> {
    await expect(this.cartBadge).toHaveText(count);
  }

  /**
   * Assert the cart is empty.
   *
   * Hazard, plan §6.4: when the cart is empty the badge is **removed from the
   * DOM**, not hidden. `toHaveCount(0)` is therefore the correct assertion —
   * an invisibility check would pass for the wrong reason, and asserting that
   * the badge text is empty fails outright because there is no element.
   */
  async expectCartBadgeAbsent(): Promise<void> {
    await expect(this.cartBadge).toHaveCount(0);
  }

  /**
   * Assert no error is showing.
   *
   * The banner element is always present and merely empty when there is no
   * error, so this asserts on text rather than on absence (plan §1.4).
   */
  async expectNoError(): Promise<void> {
    await expect(this.errorBanner).toHaveText('');
  }

  async expectError(message: string): Promise<void> {
    await expect(this.errorBanner).toHaveText(message);
  }
}
