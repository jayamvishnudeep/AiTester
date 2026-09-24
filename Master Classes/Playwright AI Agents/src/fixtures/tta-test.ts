// spec: specs/ttacart-e2e-order-plan.md
//
// The project's test entry point. Specs import `test` and `expect` from here
// rather than from @playwright/test, which is what gets them the page objects
// and — more importantly — the storage reset below.

import { test as base } from '@playwright/test';
import { CartPage } from '../pages/CartPage';
import { CheckoutCompletePage } from '../pages/CheckoutCompletePage';
import { CheckoutInformationPage } from '../pages/CheckoutInformationPage';
import { CheckoutOverviewPage } from '../pages/CheckoutOverviewPage';
import { InventoryPage } from '../pages/InventoryPage';
import { LoginPage } from '../pages/LoginPage';
import { OrderFlow } from '../flows/OrderFlow';
import { APP_URL } from './test-data';

export interface TTACartFixtures {
  loginPage: LoginPage;
  inventoryPage: InventoryPage;
  cartPage: CartPage;
  checkoutInformationPage: CheckoutInformationPage;
  checkoutOverviewPage: CheckoutOverviewPage;
  checkoutCompletePage: CheckoutCompletePage;
  orderFlow: OrderFlow;
  cleanSession: void;
}

export const test = base.extend<TTACartFixtures>({
  /**
   * DO NOT REMOVE — but not for the reason you might assume.
   *
   * Hazard, plan §6.3: TTACart persists the checkout details to localStorage
   * under `tta-cart-checkout-info`, checkout step one pre-fills from that key,
   * and the key survives a completed order. If a test reaches step one with
   * that key already set, the blank-field negatives (§4.1 – §4.4) arrive at a
   * populated form, the validation they exist to exercise never fires, and all
   * four pass while testing nothing at all — green, silent, and worthless.
   *
   * MEASURED, 2026-09-25: with this fixture disabled the eight checkout
   * negatives still pass, because Playwright gives every test a fresh browser
   * context and therefore empty storage. So under the CURRENT config this is
   * insurance, not the thing holding those tests up.
   *
   * It stays because the insurance is against a specific and likely change:
   * the moment anyone adds `storageState` to reuse a login across tests — the
   * standard next optimisation for a page-object suite, and an obvious one
   * here given every scenario logs in — storage stops being per-test and this
   * becomes the only thing standing between §4.1 – §4.4 and a silent false
   * pass. Sharing a context via serial mode does the same.
   *
   * `page.evaluate` is used deliberately and is the one exception to this
   * project's rule that everything goes through web-first expect(locator)
   * assertions: this is fixture teardown of browser storage, for which
   * Playwright exposes no API, and the MCP server's browser_localstorage_*
   * tools advertise but resolve as "not found" on this build.
   *
   * It runs automatically for every test — `auto: true` — so a new spec cannot
   * forget it.
   */
  cleanSession: [
    async ({ page }, use) => {
      await page.goto(APP_URL);
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
      await use();
    },
    { auto: true },
  ],

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

  orderFlow: async (
    {
      loginPage,
      inventoryPage,
      cartPage,
      checkoutInformationPage,
      checkoutOverviewPage,
    },
    use,
  ) => {
    await use(
      new OrderFlow(
        loginPage,
        inventoryPage,
        cartPage,
        checkoutInformationPage,
        checkoutOverviewPage,
      ),
    );
  },
});

export { expect } from '@playwright/test';
