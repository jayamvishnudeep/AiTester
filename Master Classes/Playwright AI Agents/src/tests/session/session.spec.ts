// spec: specs/ttacart-extended-negative-plan.md §8.5 – §8.6
// seed: src/tests/seed.spec.ts

import { expect, test } from '@fixtures/test-base';
import {
  EMPTY_ORDER_TOTALS,
  FIRST_ITEM,
  STORAGE_KEYS,
  URLS,
} from '@testdata/ttacart.data';

test.describe('Session', () => {
  // ------------------------------------------------------------------- §8.5
  test('Logout ends the session and the route guard holds @p0', async ({
    page,
    loggedIn,
    inventoryPage,
    loginPage,
  }) => {
    void loggedIn;
    await inventoryPage.addFirstItemToCart();

    await inventoryPage.logout();

    await loginPage.expectLoaded();
    // The session is genuinely gone.
    expect(await loginPage.readStorageKey(STORAGE_KEYS.user)).toBeNull();

    // And the route guard still refuses a deep link.
    await page.goto(URLS.inventory);
    await loginPage.expectLoaded();

    // PINS A SUSPECTED BUG (addendum §9.3): logout does NOT clear the cart.
    // tta-cart-items survives, so the next person to sign in on a shared machine
    // inherits the previous person's cart. Asserting current behaviour so that a
    // fix fails loudly. Passing is not approval.
    expect(await loginPage.readStorageKey(STORAGE_KEYS.items)).toBe(
      `["${FIRST_ITEM.id}"]`,
    );
  });

  // ------------------------------------------------------------------- §8.6
  test('Reset App State clears the cart and saved details but keeps the session', async ({
    atCheckoutOverview,
    checkoutOverviewPage,
  }) => {
    void atCheckoutOverview;
    // Reaching the overview saved the checkout details to storage.
    expect(
      await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.checkoutInfo),
    ).not.toBeNull();

    await checkoutOverviewPage.resetAppState();

    // The cart and the saved details go; the session stays.
    await expect(checkoutOverviewPage.lineItems).toHaveCount(0);
    await checkoutOverviewPage.expectTotals(EMPTY_ORDER_TOTALS);
    expect(
      await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.items),
    ).toBeNull();
    expect(
      await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.checkoutInfo),
    ).toBeNull();
    expect(
      await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.user),
    ).not.toBeNull();
  });
});
