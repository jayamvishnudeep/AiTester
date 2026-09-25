// spec: specs/ttacart-extended-negative-plan.md §8
// seed: src/seed.spec.ts
//
// Paths the primary plan checks for existence but never exercises — Remove,
// Continue Shopping, Back Home, the burger menu, the sort dropdown — plus the
// class of route it never probes at all: reaching a checkout step by URL rather
// than by clicking through to it.
//
// Four of these pin suspected bugs (addendum §9). The most consequential is
// §8.8: checkout step two renders for any signed-in user whether or not step one
// was ever completed, which means the four blank-field negatives in the primary
// plan guard a door with an open wall beside it. Those tests are still correct —
// the form does validate — they just are not evidence that the details cannot be
// skipped.

import { expect, test } from '../fixtures/tta-test';
import {
  CONFIRMATION,
  CREDENTIALS,
  EMPTY_ORDER_TOTALS,
  FIRST_ITEM,
  HEADINGS,
  INVENTORY_COUNT,
  LAST_ITEM_ALPHABETICALLY,
  STORAGE_KEYS,
  TITLES,
  URLS,
} from '../fixtures/test-data';

test.describe('TTACart — extended negative and alternate paths', () => {
  // ------------------------------------------------------------------- §8.1
  test('Removing the only item empties the cart', async ({ orderFlow, cartPage }) => {
    // 1. Log in, add the first item, open the cart.
    await orderFlow.reachCartWithFirstItem();
    await expect(cartPage.lineItems).toHaveCount(1);

    // 2. Click Remove.
    await cartPage.removeButton().click();

    await cartPage.expectAtUrl();
    await cartPage.expectEmpty();
    // The badge leaves the DOM rather than emptying (primary plan §6.4).
    await cartPage.expectCartBadgeAbsent();
    expect(await cartPage.readStorageKey(STORAGE_KEYS.items)).toBe('[]');

    // Same defect as primary-plan §6.1 by a different route: Checkout is STILL
    // offered on the emptied cart, and leads to a completable $0.00 order.
    // Pinned, not endorsed — see addendum §9.4.
    await expect(cartPage.checkoutLink).toBeVisible();
  });

  // ------------------------------------------------------------------- §8.2
  test('Continue Shopping returns to the products page with the cart intact', async ({
    orderFlow,
    cartPage,
    inventoryPage,
  }) => {
    // 1. Log in, add the first item, open the cart.
    await orderFlow.reachCartWithFirstItem();

    // 2. Click Continue Shopping (an anchor, not a button — plan §6.5).
    await cartPage.continueShoppingLink.click();

    await inventoryPage.expectLoaded();
    await expect(inventoryPage.items).toHaveCount(INVENTORY_COUNT);
    // Navigating away does not discard the cart.
    await inventoryPage.expectCartBadgeCount('1');
  });

  // ------------------------------------------------------------------- §8.3
  test('Back Home from the confirmation page returns to the products page', async ({
    orderFlow,
    checkoutOverviewPage,
    checkoutCompletePage,
    inventoryPage,
  }) => {
    // 1. Complete an order.
    await orderFlow.reachOverviewWithFirstItem();
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();

    // 2. Click Back Home.
    await checkoutCompletePage.backHomeButton.click();

    await inventoryPage.expectLoaded();
    await expect(inventoryPage.items).toHaveCount(INVENTORY_COUNT);
    await inventoryPage.expectCartBadgeAbsent();

    // Direct evidence for the hazard in primary-plan §6.3: the saved checkout
    // details OUTLIVE the completed order. This is why the suite resets storage.
    expect(await inventoryPage.readStorageKey(STORAGE_KEYS.checkoutInfo)).toBe(
      '{"firstName":"John","lastName":"Doe","postal":"12345"}',
    );
  });

  // ------------------------------------------------------------------- §8.4
  test('Sorting Z to A changes which product comes first', async ({
    orderFlow,
    inventoryPage,
  }) => {
    // 1. Log in. The default sort is Name (A to Z).
    await orderFlow.loginAsStandardUser();
    await inventoryPage.expectDefaultSort();
    await expect(inventoryPage.itemNames.first()).toHaveText(FIRST_ITEM.name);

    // 2. Switch to Name (Z to A).
    await inventoryPage.sortBy('za');

    await expect(inventoryPage.itemNames.first()).toHaveText(LAST_ITEM_ALPHABETICALLY);
    await expect(inventoryPage.items).toHaveCount(INVENTORY_COUNT);
  });

  // ------------------------------------------------------------------- §8.5
  test('Logout ends the session and the route guard holds', async ({
    page,
    orderFlow,
    inventoryPage,
    loginPage,
  }) => {
    // 1. Log in and add the first item.
    await orderFlow.loginAsStandardUser();
    await inventoryPage.addFirstItemToCart();

    // 2. Open the burger menu and click Logout.
    await inventoryPage.logout();

    await loginPage.expectLoaded();
    // The session is genuinely gone.
    expect(await loginPage.readStorageKey(STORAGE_KEYS.user)).toBeNull();

    // The route guard still refuses a deep link.
    await page.goto(URLS.inventory);
    await loginPage.expectLoaded();

    // PINS A SUSPECTED BUG (addendum §9.3): logout does NOT clear the cart.
    // tta-cart-items survives, so the next person to sign in on this machine
    // inherits the previous person's cart. Asserting the current behaviour so a
    // fix fails loudly. Passing is not approval.
    expect(await loginPage.readStorageKey(STORAGE_KEYS.items)).toBe(
      `["${FIRST_ITEM.id}"]`,
    );
  });

  // ------------------------------------------------------------------- §8.6
  test('Reset App State clears the cart and saved details but keeps the session', async ({
    orderFlow,
    checkoutOverviewPage,
  }) => {
    // 1. Reach the overview, which saves the checkout details to storage.
    await orderFlow.reachOverviewWithFirstItem();
    expect(await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.checkoutInfo)).not.toBeNull();

    // 2. Open the burger menu and click Reset App State.
    await checkoutOverviewPage.resetAppState();

    // The cart and the saved details go; the session stays.
    await expect(checkoutOverviewPage.lineItems).toHaveCount(0);
    await checkoutOverviewPage.expectTotals(EMPTY_ORDER_TOTALS);
    expect(await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.items)).toBeNull();
    expect(await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.checkoutInfo)).toBeNull();
    expect(await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.user)).not.toBeNull();
  });

  // ------------------------------------------------------------------- §8.7
  // PINS A SUSPECTED BUG (addendum §9.1), and the most serious of the four.
  // Finishing an order empties the cart but leaves the overview in history with
  // a live Finish button, so Back-then-Finish places a second confirmed order.
  // Repeat as often as you like. This asserts the CURRENT behaviour so that a
  // fix fails loudly and is updated deliberately. Passing is not approval.
  test('Browser Back after Finish allows a second order (pins suspected bug §9.1)', async ({
    page,
    orderFlow,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    // 1. Complete an order.
    await orderFlow.reachOverviewWithFirstItem();
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await checkoutCompletePage.expectConfirmationHeader();

    // 2. Press the browser Back button.
    await page.goBack();

    // The overview is back — emptied, but fully operable.
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.pageHeading).toHaveText(HEADINGS.checkoutStepTwo);
    await expect(checkoutOverviewPage.lineItems).toHaveCount(0);
    await checkoutOverviewPage.expectTotals(EMPTY_ORDER_TOTALS);
    await expect(checkoutOverviewPage.finishButton).toBeVisible();

    // 3. Click Finish a second time — and a second order is confirmed.
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await expect(checkoutCompletePage.header).toHaveText(CONFIRMATION.header);
  });

  // ------------------------------------------------------------------- §8.8
  // PINS A SUSPECTED BUG (addendum §9.2). Checkout step two renders for any
  // signed-in user whether or not step one was ever completed. This is the
  // finding that qualifies the primary plan's §4.1 – §4.4: the form does
  // validate, but the form is optional.
  test('Checkout step two is reachable by URL, bypassing step one (pins suspected bug §9.2)', async ({
    page,
    orderFlow,
    inventoryPage,
    checkoutOverviewPage,
  }) => {
    // 1. Log in and add the first item. Do NOT visit step one.
    await orderFlow.loginAsStandardUser();
    await inventoryPage.addFirstItemToCart();

    // 2. Navigate straight to step two.
    await page.goto(URLS.checkoutStepTwo);

    // No redirect, no error — the overview renders with the real line item.
    await checkoutOverviewPage.expectLoaded();
    await expect(checkoutOverviewPage.pageHeading).toHaveText(HEADINGS.checkoutStepTwo);
    await checkoutOverviewPage.expectSingleLineItem(FIRST_ITEM.name, FIRST_ITEM.price);
    await checkoutOverviewPage.expectCartBadgeCount('1');
    // The overview carries no error banner element at all — unlike the login
    // page and step one, which render it present-but-empty. Nothing here even
    // has the affordance to complain that step one was skipped.
    await checkoutOverviewPage.expectErrorBannerAbsent();

    // The customer details were never supplied, and were never needed.
    expect(
      await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.checkoutInfo),
    ).toBeNull();
  });

  // ------------------------------------------------------------------- §8.9
  // PINS A SUSPECTED BUG (addendum §9.2). The two defects compose: an order can
  // be completed with no cart, no customer details, and without ever loading the
  // form that validates them.
  test('Finish from a URL-reached empty overview completes an order (pins suspected bug §9.2)', async ({
    page,
    orderFlow,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    // 1. Log in and add nothing.
    await orderFlow.loginAsStandardUser();

    // 2. Navigate straight to step two.
    await page.goto(URLS.checkoutStepTwo);
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.lineItems).toHaveCount(0);
    await checkoutOverviewPage.expectTotals(EMPTY_ORDER_TOTALS);

    // 3. Click Finish.
    await expect(checkoutOverviewPage.finishButton).toBeVisible();
    await checkoutOverviewPage.finish();

    // A confirmed order for nothing, from a form never loaded.
    await checkoutCompletePage.expectLoaded();
    await expect(checkoutCompletePage.pageHeading).toHaveText(HEADINGS.checkoutComplete);
    await checkoutCompletePage.expectOrderConfirmed();
  });
});
