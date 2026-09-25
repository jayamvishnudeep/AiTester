// spec: specs/ttacart-e2e-order-plan.md §2.2
// seed: src/tests/seed.spec.ts

import { expect, test } from '@fixtures/test-base';
import {
  FIRST_ITEM,
  HEADINGS,
  INVENTORY_COUNT,
} from '@testdata/ttacart.data';

test.describe('Login', () => {
  // ------------------------------------------------------------------- §2.2
  test('Successful login lands on the products page @p0', async ({
    loggedIn,
    inventoryPage,
  }) => {
    void loggedIn;

    await inventoryPage.expectLoaded();
    await expect(inventoryPage.pageHeading).toHaveText(HEADINGS.inventory);

    // Exactly six inventory cards, default A-to-Z sort, red T-shirt first.
    await expect(inventoryPage.items).toHaveCount(INVENTORY_COUNT);
    await inventoryPage.expectDefaultSort();
    await inventoryPage.expectFirstItem(FIRST_ITEM.name, FIRST_ITEM.price);

    // The header exposes the burger menu and the cart link, and no badge because
    // the cart is empty — absent from the DOM, not hidden (plan §6.4).
    await expect(inventoryPage.primaryHeader).toBeVisible();
    await expect(inventoryPage.burgerMenu).toBeVisible();
    await expect(inventoryPage.cartLink).toBeVisible();
    await inventoryPage.expectCartBadgeAbsent();
  });
});
