// spec: specs/ttacart-e2e-order-plan.md §2.6, §4.6, addendum §8.3
// seed: src/tests/seed.spec.ts

import { expect, test } from '@fixtures/test-base';
import {
  FIRST_ITEM,
  INVENTORY_COUNT,
  ORDER_TOTALS,
  SAVED_CHECKOUT_INFO,
  STORAGE_KEYS,
} from '@testdata/ttacart.data';

test.describe('Checkout — overview step', () => {
  // ------------------------------------------------------------------- §2.6
  test('Overview shows a correct order summary @p0', async ({
    atCheckoutOverview,
    checkoutOverviewPage,
  }) => {
    void atCheckoutOverview;

    await checkoutOverviewPage.expectLoaded();
    await checkoutOverviewPage.expectSingleLineItem(
      FIRST_ITEM.name,
      FIRST_ITEM.price,
    );

    // Payment and courier strings are TTACart's own, not saucedemo's.
    await checkoutOverviewPage.expectPaymentAndShipping();

    // 8% tax on $15.99 rounds to $1.28, giving $17.27.
    await checkoutOverviewPage.expectTotals(ORDER_TOTALS);

    await expect(checkoutOverviewPage.cancelLink).toBeVisible();
    await expect(checkoutOverviewPage.finishButton).toBeVisible();
    await checkoutOverviewPage.expectCartBadgeCount('1');
  });

  // ------------------------------------------------------------------- §4.6
  test('Cancel on the overview returns to the cart', async ({
    atCheckoutOverview,
    checkoutOverviewPage,
    cartPage,
    checkoutCompletePage,
  }) => {
    void atCheckoutOverview;

    // TTACart's overview Cancel goes to the cart, not the products page as on
    // saucedemo.com.
    await checkoutOverviewPage.cancel();

    await cartPage.expectAtUrl();
    await expect(cartPage.lineItems).toHaveCount(1);
    await cartPage.expectCartBadgeCount('1');
    // The order was not placed.
    await expect(checkoutCompletePage.header).toHaveCount(0);
  });

  // ------------------------------------------------------------------- §8.3
  test('Back Home from the confirmation page returns to the products page', async ({
    atCheckoutOverview,
    checkoutOverviewPage,
    checkoutCompletePage,
    inventoryPage,
  }) => {
    void atCheckoutOverview;

    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();

    await checkoutCompletePage.backHome();

    await inventoryPage.expectLoaded();
    await expect(inventoryPage.items).toHaveCount(INVENTORY_COUNT);
    await inventoryPage.expectCartBadgeAbsent();

    // Direct evidence for the hazard in plan §6.3: the saved checkout details
    // OUTLIVE the completed order. This is why the suite resets storage.
    expect(await inventoryPage.readStorageKey(STORAGE_KEYS.checkoutInfo)).toBe(
      SAVED_CHECKOUT_INFO,
    );
  });
});
