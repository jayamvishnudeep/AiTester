// spec: specs/ttacart-e2e-order-plan.md §4.7 – §4.8, addendum §8.7 – §8.9
// seed: src/tests/seed.spec.ts
//
// ============================================================================
// EVERY TEST IN THIS FILE PINS A SUSPECTED APPLICATION BUG.
//
// They assert the behaviour the application CURRENTLY has, not the behaviour it
// should have. A green run here is not approval — it is a record that the defect
// is still present and unchanged.
//
// If the application is ever fixed, these tests are SUPPOSED to fail. That is
// their whole purpose: the fix arrives loudly, and whoever makes it updates the
// assertion deliberately instead of discovering months later that nobody noticed.
//
// They live in their own file so that "everything green except
// checkout-known-bugs" is a readable and meaningful state.
// ============================================================================

import { expect, test } from '@fixtures/test-base';
import {
  CONFIRMATION,
  CUSTOMER,
  EMPTY_ORDER_TOTALS,
  FIRST_ITEM,
  HEADINGS,
  NON_NUMERIC_POSTAL_CODE,
  ORDER_TOTALS,
  STORAGE_KEYS,
  URLS,
} from '@testdata/ttacart.data';

test.describe('Checkout — pinned suspected bugs', () => {
  // ------------------------------------------------------------------- §4.7
  // Plan §6.2: there is no length, character or numeric constraint on the postal
  // code — only "non-empty after trimming".
  test('A non-numeric postal code is accepted (pins plan §6.2)', async ({
    atCheckoutInformation,
    checkoutInformationPage,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    void atCheckoutInformation;

    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      CUSTOMER.lastName,
      NON_NUMERIC_POSTAL_CODE,
    );
    await checkoutInformationPage.continue();

    // No error is raised and the overview is reached.
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.pageHeading).toHaveText(
      HEADINGS.checkoutStepTwo,
    );
    await expect(checkoutOverviewPage.totalLabel).toHaveText(ORDER_TOTALS.total);

    // And the order finishes normally.
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await checkoutCompletePage.expectConfirmationHeader();
  });

  // ------------------------------------------------------------------- §4.8
  // Plan §6.1: an empty cart can be checked out to a completed $0.00 order. A
  // storefront should not confirm an order with nothing in it.
  test('Checking out an empty cart completes a $0.00 order (pins plan §6.1)', async ({
    emptyCart,
    cartPage,
    checkoutInformationPage,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    void emptyCart;
    await cartPage.expectEmpty();

    // Checkout is still offered, and still opens step one.
    await cartPage.checkout();
    await checkoutInformationPage.expectAtUrl();

    await checkoutInformationPage.fillValidDetails();
    await checkoutInformationPage.continue();

    // The overview renders no line items and a zero total.
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.lineItems).toHaveCount(0);
    await checkoutOverviewPage.expectTotals(EMPTY_ORDER_TOTALS);

    // And Finish confirms the order for nothing.
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await checkoutCompletePage.expectConfirmationHeader();
  });

  // ------------------------------------------------------------------- §8.7
  // Addendum §9.1, the most serious of the set. Finishing empties the cart but
  // leaves the overview in history with a live Finish button, so Back-then-Finish
  // places a second confirmed order. Repeat as often as you like.
  test('Browser Back after Finish allows a second order (pins addendum §9.1)', async ({
    page,
    atCheckoutOverview,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    void atCheckoutOverview;

    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await checkoutCompletePage.expectConfirmationHeader();

    await page.goBack();

    // The overview is back — emptied, but fully operable.
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.pageHeading).toHaveText(
      HEADINGS.checkoutStepTwo,
    );
    await expect(checkoutOverviewPage.lineItems).toHaveCount(0);
    await checkoutOverviewPage.expectTotals(EMPTY_ORDER_TOTALS);
    await expect(checkoutOverviewPage.finishButton).toBeVisible();

    // A second order is confirmed.
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await expect(checkoutCompletePage.header).toHaveText(CONFIRMATION.header);
  });

  // ------------------------------------------------------------------- §8.8
  // Addendum §9.2. Step two renders for any signed-in user whether or not step
  // one was completed. This is the finding that qualifies §4.1 – §4.4: the form
  // validates, but the form is optional.
  test('Checkout step two is reachable by URL, bypassing step one (pins addendum §9.2)', async ({
    page,
    loggedIn,
    inventoryPage,
    checkoutOverviewPage,
  }) => {
    void loggedIn;
    await inventoryPage.addFirstItemToCart();

    // Straight to step two, never having visited step one.
    await page.goto(URLS.checkoutStepTwo);

    // No redirect, no error — the overview renders with the real line item.
    await checkoutOverviewPage.expectLoaded();
    await checkoutOverviewPage.expectSingleLineItem(
      FIRST_ITEM.name,
      FIRST_ITEM.price,
    );
    await checkoutOverviewPage.expectCartBadgeCount('1');
    // The overview carries no error banner element at all — unlike the login page
    // and step one, which render it present-but-empty. Nothing here even has the
    // affordance to complain that step one was skipped.
    await checkoutOverviewPage.expectErrorBannerAbsent();

    // The customer details were never supplied, and were never needed.
    expect(
      await checkoutOverviewPage.readStorageKey(STORAGE_KEYS.checkoutInfo),
    ).toBeNull();
  });

  // ------------------------------------------------------------------- §8.9
  // Addendum §9.2, composed with §9.1's sibling: an order can be completed with
  // no cart, no customer details, and without ever loading the form that
  // validates them.
  test('Finish from a URL-reached empty overview completes an order (pins addendum §9.2)', async ({
    page,
    loggedIn,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    void loggedIn;

    await page.goto(URLS.checkoutStepTwo);
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.lineItems).toHaveCount(0);
    await checkoutOverviewPage.expectTotals(EMPTY_ORDER_TOTALS);

    await expect(checkoutOverviewPage.finishButton).toBeVisible();
    await checkoutOverviewPage.finish();

    await checkoutCompletePage.expectLoaded();
    await expect(checkoutCompletePage.pageHeading).toHaveText(
      HEADINGS.checkoutComplete,
    );
    await checkoutCompletePage.expectOrderConfirmed();
  });
});
