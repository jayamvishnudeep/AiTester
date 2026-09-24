// spec: specs/ttacart-e2e-order-plan.md

import { CartPage } from '../pages/CartPage';
import { CheckoutInformationPage } from '../pages/CheckoutInformationPage';
import { CheckoutOverviewPage } from '../pages/CheckoutOverviewPage';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';
import { CREDENTIALS } from '../fixtures/test-data';

/**
 * Multi-page preconditions.
 *
 * These are the journeys a scenario has to travel through before the thing it
 * actually tests becomes reachable — "logged in, one item in the cart, sitting
 * on checkout step one" is the precondition for eight of the negatives.
 *
 * They live here rather than on a page object because no single page owns them:
 * a method that logs in, adds an item and lands on checkout belongs to none of
 * LoginPage, InventoryPage or CartPage individually. Keeping them out of the
 * page classes is what stops those classes from slowly turning into a
 * god-object of every route through the app.
 */
export class OrderFlow {
  constructor(
    private readonly loginPage: LoginPage,
    private readonly inventoryPage: InventoryPage,
    private readonly cartPage: CartPage,
    private readonly checkoutInformationPage: CheckoutInformationPage,
    private readonly checkoutOverviewPage: CheckoutOverviewPage,
  ) {}

  /** Log in as the standard user and assert the products page was reached. */
  async loginAsStandardUser(): Promise<void> {
    await this.loginPage.goto();
    await this.loginPage.loginAs(CREDENTIALS.username, CREDENTIALS.password);
  }

  /** Logged in, first item added, sitting on the cart page. */
  async reachCartWithFirstItem(): Promise<void> {
    await this.loginAsStandardUser();
    await this.inventoryPage.addFirstItemToCart();
    await this.inventoryPage.openCart();
    await this.cartPage.expectAtUrl();
  }

  /**
   * Logged in as the standard user, one red T-shirt in the cart, on checkout
   * step one. The precondition for plan §4.1 – §4.7.
   */
  async reachCheckoutStepOne(): Promise<void> {
    await this.reachCartWithFirstItem();
    await this.cartPage.checkout();
    await this.checkoutInformationPage.expectAtUrl();
  }

  /**
   * As above, then through step one with valid details, landing on the
   * overview. The precondition for §2.6, §2.7 and §4.6.
   */
  async reachOverviewWithFirstItem(): Promise<void> {
    await this.reachCheckoutStepOne();
    await this.checkoutInformationPage.fillValidDetails();
    await this.checkoutInformationPage.continue();
    await this.checkoutOverviewPage.expectAtUrl();
  }

  /**
   * Logged in with nothing added, on the cart page.
   * The precondition for the empty-cart bug pinned in §4.8.
   */
  async reachEmptyCart(): Promise<void> {
    await this.loginAsStandardUser();
    await this.inventoryPage.expectCartBadgeAbsent();
    await this.inventoryPage.openCart();
    await this.cartPage.expectAtUrl();
  }
}
