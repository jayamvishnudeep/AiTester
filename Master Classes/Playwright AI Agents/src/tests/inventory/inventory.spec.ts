// spec: specs/ttacart-e2e-order-plan.md §2.3, addendum §8.4
// seed: src/tests/seed.spec.ts

import { expect, test } from '@fixtures/test-base';
import {
  FIRST_ITEM,
  INVENTORY_COUNT,
  LAST_ITEM_ALPHABETICALLY,
  SORT_OPTIONS,
} from '@testdata/ttacart.data';

test.describe('Inventory', () => {
  // ------------------------------------------------------------------- §2.3
  test('Cart badge updates when the first item is added @p0', async ({
    loggedIn,
    inventoryPage,
  }) => {
    void loggedIn;
    await inventoryPage.expectCartBadgeAbsent();

    await inventoryPage.addToCartButton().click();

    await inventoryPage.expectCartBadgeCount('1');

    // The button re-renders as Remove, and its data-test attribute flips with it
    // — add and remove are two different elements, not one changing label.
    const removeButton = inventoryPage.removeButton();
    await expect(removeButton).toHaveText('Remove');
    await expect(removeButton).toHaveClass('item-btn is-remove');
    await expect(inventoryPage.addToCartButton()).toHaveCount(0);

    // No navigation.
    await inventoryPage.expectAtUrl();
  });

  // ------------------------------------------------------------------- §8.4
  test('Sorting Z to A changes which product comes first', async ({
    loggedIn,
    inventoryPage,
  }) => {
    void loggedIn;
    await inventoryPage.expectDefaultSort();
    await inventoryPage.expectFirstItem(FIRST_ITEM.name);

    await inventoryPage.sortBy(SORT_OPTIONS.nameDesc);

    await inventoryPage.expectFirstItem(LAST_ITEM_ALPHABETICALLY);
    await expect(inventoryPage.items).toHaveCount(INVENTORY_COUNT);
  });
});
