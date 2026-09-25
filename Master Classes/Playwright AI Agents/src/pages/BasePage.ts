// spec: specs/ttacart-e2e-order-plan.md §1.2, §6.4
//
// Shared infrastructure for every page object: the page handle, the element
// factory (`el`), a scoped logger (`log`), and the signed-in header shell.
//
// The shell belongs here because it is rendered on all five signed-in pages, and
// the error banner because it is reused by the two pages that can raise one.
// Subclasses declare only their own domain.
//
// On assertions in page objects: the expect* helpers here are limited to page
// IDENTITY and SHELL STATE — "am I on the right page", "is the badge what I
// think". Everything a specific scenario claims stays in the spec, where a
// reader can see what the test actually asserts.

import { expect, type Locator, type Page } from '@playwright/test';
import { createLogger, type Logger } from '../utils/logger';
import { elementFactory, type UtilElementLocator } from '../utils/UtilElementLocator';

export abstract class BasePage {
  readonly page: Page;
  protected readonly log: Logger;
  protected readonly el: (selector: string, description: string) => UtilElementLocator;

  /** The URL the browser reports for this page, extension-less (plan §1.1). */
  abstract readonly url: string;
  /** `document.title` for this page. */
  abstract readonly title: string;

  // --- the signed-in shell, rendered on every page but login (plan §1.2) ------
  private readonly primaryHeaderEl: Locator;
  private readonly burgerMenuEl: Locator;
  private readonly cartLinkEl: Locator;
  private readonly cartBadgeEl: Locator;
  private readonly pageHeadingEl: Locator;
  private readonly errorBannerEl: Locator;

  // --- the burger sidebar (addendum §8.5 – §8.6) ------------------------------
  private readonly closeMenuEl: Locator;
  private readonly allItemsLinkEl: Locator;
  private readonly logoutLinkEl: Locator;
  private readonly resetAppStateLinkEl: Locator;

  protected constructor(page: Page, scope: string) {
    this.page = page;
    this.log = createLogger(scope);
    this.el = elementFactory(page, scope);

    this.primaryHeaderEl = page.locator('[data-test="primary-header"]');
    this.burgerMenuEl = page.locator('[data-test="open-menu"]');
    this.cartLinkEl = page.locator('[data-test="shopping-cart-link"]');
    this.cartBadgeEl = page.locator('[data-test="shopping-cart-badge"]');
    this.pageHeadingEl = page.locator('[data-test="title"]');
    this.errorBannerEl = page.locator('[data-test="error"]');

    this.closeMenuEl = page.locator('[data-test="close-menu"]');
    this.allItemsLinkEl = page.locator('[data-test="inventory-sidebar-link"]');
    this.logoutLinkEl = page.locator('[data-test="logout-sidebar-link"]');
    this.resetAppStateLinkEl = page.locator('[data-test="reset-sidebar-link"]');
  }

  // Locators the specs assert against are exposed read-only; the raw fields stay
  // private so a spec cannot reach past the page object and click them directly.
  get primaryHeader(): Locator {
    return this.primaryHeaderEl;
  }
  get burgerMenu(): Locator {
    return this.burgerMenuEl;
  }
  get cartLink(): Locator {
    return this.cartLinkEl;
  }
  get cartBadge(): Locator {
    return this.cartBadgeEl;
  }
  get pageHeading(): Locator {
    return this.pageHeadingEl;
  }
  get errorBanner(): Locator {
    return this.errorBannerEl;
  }

  // --- navigation ------------------------------------------------------------

  async goto(): Promise<void> {
    this.log.info(`goto ${this.url}`);
    await this.page.goto(this.url);
  }

  async openCart(): Promise<void> {
    this.log.info('open cart from the header');
    await this.cartLinkEl.click();
  }

  /**
   * Open the burger sidebar and wait for it to finish sliding in.
   *
   * The wait is on a link being visible rather than present: the sidebar is in
   * the DOM before it is reachable, so clicking without this is a race.
   */
  async openMenu(): Promise<void> {
    this.log.info('open the burger menu');
    await this.burgerMenuEl.click();
    await expect(this.logoutLinkEl).toBeVisible();
  }

  async logout(): Promise<void> {
    await this.openMenu();
    this.log.info('logout');
    await this.logoutLinkEl.click();
  }

  /**
   * Reset App State — clears `tta-cart-items` and `tta-cart-checkout-info` and
   * leaves `tta-cart-user`, so the session survives (addendum §8.6). Note that
   * logout does NOT clear the cart; see addendum §9.3.
   */
  async resetAppState(): Promise<void> {
    await this.openMenu();
    this.log.info('reset app state');
    await this.resetAppStateLinkEl.click();
  }

  async closeMenu(): Promise<void> {
    await this.closeMenuEl.click();
  }

  async goToAllItems(): Promise<void> {
    await this.openMenu();
    await this.allItemsLinkEl.click();
  }

  // --- state -----------------------------------------------------------------

  /** Read a localStorage key, or null when absent. */
  async readStorageKey(key: string): Promise<string | null> {
    return this.page.evaluate((k) => localStorage.getItem(k), key);
  }

  // --- identity and shell assertions -----------------------------------------

  async expectLoaded(): Promise<void> {
    await expect(this.page).toHaveURL(this.url);
    await expect(this.page).toHaveTitle(this.title);
  }

  /** URL only — for steps where the title is not the point. */
  async expectAtUrl(): Promise<void> {
    await expect(this.page).toHaveURL(this.url);
  }

  async expectCartBadgeCount(count: string): Promise<void> {
    await expect(this.cartBadgeEl).toHaveText(count);
  }

  /**
   * Assert the cart is empty.
   *
   * Hazard, plan §6.4: when the cart is empty the badge is REMOVED from the DOM,
   * not hidden. toHaveCount(0) is therefore the correct assertion — an
   * invisibility check passes for the wrong reason, and asserting the badge text
   * is empty fails outright because there is no element to read.
   */
  async expectCartBadgeAbsent(): Promise<void> {
    await expect(this.cartBadgeEl).toHaveCount(0);
  }

  /**
   * Assert no error is showing.
   *
   * The banner element is present and merely empty when there is no error, so
   * this asserts on text rather than absence (plan §1.4).
   */
  async expectNoError(): Promise<void> {
    await expect(this.errorBannerEl).toHaveText('');
  }

  async expectError(message: string): Promise<void> {
    await expect(this.errorBannerEl).toHaveText(message);
  }

  /**
   * Assert this page has no error banner element at all.
   *
   * A real property of the application, not a style choice. The banner exists —
   * present but empty — only on the login page and checkout step one, the two
   * pages that can raise an error. On products, cart, overview and confirmation
   * it is absent from the DOM, so toHaveText('') fails there rather than passing.
   */
  async expectErrorBannerAbsent(): Promise<void> {
    await expect(this.errorBannerEl).toHaveCount(0);
  }
}
