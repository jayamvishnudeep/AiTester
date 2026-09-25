// spec: specs/ttacart-e2e-order-plan.md
//
// The project's test entry point. Specs import `test` and `expect` from here,
// never from @playwright/test directly — that import is what supplies the page
// objects, the composable state fixtures, and the storage reset.
//
// The state fixtures COMPOSE: each one depends on the previous, so requesting
// the deepest automatically runs the stack beneath it. A spec asks for the state
// it needs and says nothing about how to get there:
//
//   loggedIn  ->  cartWithItem  ->  atCheckoutInformation  ->  atCheckoutOverview
//
// This replaces the flow helpers an earlier version kept in a separate class. The
// difference is not cosmetic: a fixture is requested by name in the test
// signature, so the precondition is visible in the test's own declaration rather
// than buried in its first line.

import { test as base } from '@playwright/test';
import { CartPage } from '../pages/CartPage';
import { CheckoutCompletePage } from '../pages/CheckoutCompletePage';
import { CheckoutInformationPage } from '../pages/CheckoutInformationPage';
import { CheckoutOverviewPage } from '../pages/CheckoutOverviewPage';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';
import { assertEnv } from '../config/env';
import { standardUser } from '../config/credentials';
import { APP_URL } from '../testdata/ttacart.data';

export interface TTACartPages {
  loginPage: LoginPage;
  inventoryPage: InventoryPage;
  cartPage: CartPage;
  checkoutInformationPage: CheckoutInformationPage;
  checkoutOverviewPage: CheckoutOverviewPage;
  checkoutCompletePage: CheckoutCompletePage;
}

export interface TTACartState {
  /** Auto: a clean session before every test. See the comment on it. */
  cleanSession: void;
  /** Signed in as the standard user, on the products page. */
  loggedIn: void;
  /** Signed in with the first item added, on the cart page. */
  cartWithItem: void;
  /** Signed in with nothing added, on the cart page. */
  emptyCart: void;
  /** Signed in with one item, on checkout step one. */
  atCheckoutInformation: void;
  /** As above, then through step one with valid details, on the overview. */
  atCheckoutOverview: void;
}

export type TTACartFixtures = TTACartPages & TTACartState;

export const test = base.extend<TTACartFixtures>({
  // --- page objects ---------------------------------------------------------
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  inventoryPage: async ({ page }, use) => {
    await use(new InventoryPage(page));
  },
  cartPage: async ({ page }, use) => {
    await use(new CartPage(page));
  },
  checkoutInformationPage: async ({ page }, use) => {
    await use(new CheckoutInformationPage(page));
  },
  checkoutOverviewPage: async ({ page }, use) => {
    await use(new CheckoutOverviewPage(page));
  },
  checkoutCompletePage: async ({ page }, use) => {
    await use(new CheckoutCompletePage(page));
  },

  /**
   * DO NOT REMOVE — but not for the reason you might assume.
   *
   * Hazard, plan §6.3: TTACart persists the checkout details to localStorage
   * under `tta-cart-checkout-info`, checkout step one pre-fills from that key,
   * and the key survives a completed order. A test that reaches step one with
   * that key already set arrives at a populated form, the validation it exists to
   * exercise never fires, and it passes while testing nothing at all.
   *
   * MEASURED, 2026-09-25: with this fixture disabled the checkout negatives still
   * pass, because Playwright gives every test a fresh browser context and
   * therefore empty storage. Under the CURRENT config this is insurance, not the
   * thing holding those tests up.
   *
   * It stays because the insurance is against a specific and likely change: the
   * moment anyone adds `storageState` to reuse a login across tests — the obvious
   * next optimisation for a suite where every scenario logs in — storage stops
   * being per-test and this becomes the only thing standing between the
   * blank-field negatives and a silent false pass. Serial mode sharing a context
   * does the same.
   *
   * `page.evaluate` here is the one deliberate exception to this project's rule
   * that everything goes through web-first expect(locator) assertions: this is
   * fixture teardown of browser storage, for which Playwright exposes no API.
   */
  cleanSession: [
    async ({ page }, use) => {
      assertEnv('TTA_USERNAME', 'TTA_PASSWORD');
      await page.goto(APP_URL);
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
      await use();
    },
    { auto: true },
  ],

  // --- composable state ----------------------------------------------------
  loggedIn: async ({ loginPage }, use) => {
    await loginPage.goto();
    await loginPage.loginAs(standardUser.username, standardUser.password);
    await use();
  },

  cartWithItem: async ({ loggedIn, inventoryPage, cartPage }, use) => {
    void loggedIn;
    await inventoryPage.addFirstItemToCart();
    await inventoryPage.openCart();
    await cartPage.expectAtUrl();
    await use();
  },

  emptyCart: async ({ loggedIn, inventoryPage, cartPage }, use) => {
    void loggedIn;
    await inventoryPage.expectCartBadgeAbsent();
    await inventoryPage.openCart();
    await cartPage.expectAtUrl();
    await use();
  },

  atCheckoutInformation: async (
    { cartWithItem, cartPage, checkoutInformationPage },
    use,
  ) => {
    void cartWithItem;
    await cartPage.checkout();
    await checkoutInformationPage.expectAtUrl();
    await use();
  },

  atCheckoutOverview: async (
    { atCheckoutInformation, checkoutInformationPage, checkoutOverviewPage },
    use,
  ) => {
    void atCheckoutInformation;
    await checkoutInformationPage.fillValidDetails();
    await checkoutInformationPage.continue();
    await checkoutOverviewPage.expectAtUrl();
    await use();
  },
});

export { expect } from '@playwright/test';
