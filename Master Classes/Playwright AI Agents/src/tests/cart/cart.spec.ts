// spec: specs/ttacart-e2e-order-plan.md §2.4, addendum §8.1 – §8.2
// seed: src/tests/seed.spec.ts

import { expect, test } from '@fixtures/test-base';
import {
  FIRST_ITEM,
  HEADINGS,
  INVENTORY_COUNT,
  STORAGE_KEYS,
} from '@testdata/ttacart.data';

test.describe('Cart', () => {
  // ------------------------------------------------------------------- §2.4
  test('Cart page shows the correct line item @p0', async ({
    cartWithItem,
    cartPage,
  }) => {
    void cartWithItem;

    await cartPage.expectLoaded();
    await expect(cartPage.pageHeading).toHaveText(HEADINGS.cart);
    await cartPage.expectSingleLineItem(FIRST_ITEM.name, FIRST_ITEM.price);
    await cartPage.expectCartBadgeCount('1');

    await expect(cartPage.removeButton()).toBeVisible();
    // The markup still carries the .html hrefs even though the server serves the
    // extension-less URLs (plan §1.1).
    await expect(cartPage.continueShoppingLink).toHaveAttribute(
      'href',
      './inventory.html',
    );
    await expect(cartPage.checkoutLink).toHaveAttribute(
      'href',
      './checkout-step-one.html',
    );
  });

  // ------------------------------------------------------------------- §8.1
  test('Removing the only item empties the cart', async ({
    cartWithItem,
    cartPage,
  }) => {
    void cartWithItem;
    await expect(cartPage.lineItems).toHaveCount(1);

    await cartPage.removeFirstItem();

    await cartPage.expectAtUrl();
    await cartPage.expectEmpty();
    // The badge leaves the DOM rather than emptying (plan §6.4).
    await cartPage.expectCartBadgeAbsent();
    expect(await cartPage.readStorageKey(STORAGE_KEYS.items)).toBe('[]');

    // Same defect as plan §6.1 by a different route: Checkout is STILL offered on
    // the emptied cart, and leads to a completable $0.00 order. Pinned, not
    // endorsed — addendum §9.4.
    await expect(cartPage.checkoutLink).toBeVisible();
  });

  // ------------------------------------------------------------------- §8.2
  test('Continue Shopping returns to the products page with the cart intact', async ({
    cartWithItem,
    cartPage,
    inventoryPage,
  }) => {
    void cartWithItem;

    await cartPage.continueShopping();

    await inventoryPage.expectLoaded();
    await expect(inventoryPage.items).toHaveCount(INVENTORY_COUNT);
    // Navigating away does not discard the cart.
    await inventoryPage.expectCartBadgeCount('1');
  });
});
