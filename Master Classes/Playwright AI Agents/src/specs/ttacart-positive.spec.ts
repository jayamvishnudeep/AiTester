// spec: specs/ttacart-e2e-order-plan.md §2
// seed: src/seed.spec.ts

import { expect, test } from '../fixtures/tta-test';
import {
  CREDENTIALS,
  FIRST_ITEM,
  HEADINGS,
  INVENTORY_COUNT,
  ORDER_TOTALS,
  TITLES,
} from '../fixtures/test-data';

test.describe('TTACart — positive cases', () => {
  // ------------------------------------------------------------------- §2.1
  test('Full happy path: login, add first item, checkout, confirmation', async ({
    page,
    loginPage,
    inventoryPage,
    cartPage,
    checkoutInformationPage,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    // 1. Navigate to the login page.
    await loginPage.goto();
    await expect(page).toHaveTitle(TITLES.login);
    await loginPage.expectNoError();

    // 2-4. Enter the credentials and click Login.
    await loginPage.loginAs(CREDENTIALS.username, CREDENTIALS.password);
    await expect(inventoryPage.pageHeading).toHaveText(HEADINGS.inventory);

    // 5. Add the first inventory card to the cart.
    await inventoryPage.addFirstItemToCart();

    // 6. Open the cart from the header.
    await inventoryPage.openCart();
    await cartPage.expectAtUrl();
    await expect(cartPage.itemName).toHaveText(FIRST_ITEM.name);

    // 7. Click Checkout (an anchor, not a button).
    await cartPage.checkout();
    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectNoError();

    // 8. Enter the customer details.
    await checkoutInformationPage.fillValidDetails();

    // 9. Click Continue.
    await checkoutInformationPage.continue();
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.pageHeading).toHaveText(HEADINGS.checkoutStepTwo);
    await expect(checkoutOverviewPage.totalLabel).toHaveText(ORDER_TOTALS.total);

    // 10. Click Finish.
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await checkoutCompletePage.expectOrderConfirmed();

    // Finishing empties the cart, and the badge is removed from the DOM
    // rather than hidden — plan §6.4.
    await checkoutCompletePage.expectCartBadgeAbsent();
  });

  // ------------------------------------------------------------------- §2.2
  test('Successful login lands on the products page', async ({
    loginPage,
    inventoryPage,
  }) => {
    // 1-2. Navigate to the login page, sign in as the standard user.
    await loginPage.goto();
    await loginPage.loginAs(CREDENTIALS.username, CREDENTIALS.password);

    await inventoryPage.expectLoaded();
    await expect(inventoryPage.pageHeading).toHaveText(HEADINGS.inventory);

    // Exactly six inventory cards, default A-to-Z sort, red T-shirt first.
    await expect(inventoryPage.items).toHaveCount(INVENTORY_COUNT);
    await inventoryPage.expectDefaultSort();
    await expect(inventoryPage.itemNames.first()).toHaveText(FIRST_ITEM.name);
    await expect(inventoryPage.itemPrices.first()).toHaveText(FIRST_ITEM.price);

    // Header exposes the burger menu and the cart link, and no badge because
    // the cart is empty (absent from the DOM, not hidden — plan §6.4).
    await expect(inventoryPage.primaryHeader).toBeVisible();
    await expect(inventoryPage.burgerMenu).toBeVisible();
    await expect(inventoryPage.cartLink).toBeVisible();
    await inventoryPage.expectCartBadgeAbsent();
  });

  // ------------------------------------------------------------------- §2.3
  test('Cart badge updates when the first item is added', async ({
    orderFlow,
    inventoryPage,
  }) => {
    // 1. Log in as the standard user.
    await orderFlow.loginAsStandardUser();
    await inventoryPage.expectCartBadgeAbsent();

    // 2. Click Add to cart on the first inventory card.
    await inventoryPage.addToCartButton().click();

    await inventoryPage.expectCartBadgeCount('1');

    // The button re-renders as Remove; its data-test attribute flips too.
    const removeButton = inventoryPage.removeButton();
    await expect(removeButton).toHaveText('Remove');
    await expect(removeButton).toHaveClass('item-btn is-remove');
    await expect(inventoryPage.addToCartButton()).toHaveCount(0);

    // No navigation.
    await inventoryPage.expectAtUrl();
  });

  // ------------------------------------------------------------------- §2.4
  test('Cart page shows the correct line item', async ({
    orderFlow,
    inventoryPage,
    cartPage,
  }) => {
    // 1. Log in as the standard user and add the first item.
    await orderFlow.loginAsStandardUser();
    await inventoryPage.addFirstItemToCart();

    // 2. Click the cart link in the header.
    await inventoryPage.openCart();

    await cartPage.expectLoaded();
    await expect(cartPage.pageHeading).toHaveText(HEADINGS.cart);
    await cartPage.expectSingleLineItem(FIRST_ITEM.name, FIRST_ITEM.price);
    await cartPage.expectCartBadgeCount('1');

    await expect(cartPage.removeButton()).toBeVisible();
    // The markup still carries the .html hrefs even though the server serves
    // the extension-less URLs — plan §1.1.
    await expect(cartPage.continueShoppingLink).toHaveAttribute(
      'href',
      './inventory.html',
    );
    await expect(cartPage.checkoutLink).toHaveAttribute(
      'href',
      './checkout-step-one.html',
    );
  });

  // ------------------------------------------------------------------- §2.5
  test('Checkout information form accepts valid details and advances', async ({
    orderFlow,
    checkoutInformationPage,
    checkoutOverviewPage,
  }) => {
    // 1. Reach checkout step one with one item in the cart.
    await orderFlow.reachCheckoutStepOne();
    await checkoutInformationPage.expectLoaded();
    await expect(checkoutInformationPage.pageHeading).toHaveText(
      HEADINGS.checkoutStepOne,
    );

    // 2. Confirm the three fields start empty (true only from a clean context).
    await checkoutInformationPage.expectFieldsEmpty();

    // 3. Enter the customer details.
    await checkoutInformationPage.fillValidDetails();

    // 4. Click Continue.
    await checkoutInformationPage.continue();

    // No error banner, and the browser advances to the overview.
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.pageHeading).toHaveText(HEADINGS.checkoutStepTwo);
  });

  // ------------------------------------------------------------------- §2.6
  test('Overview page shows a correct order summary', async ({
    orderFlow,
    checkoutOverviewPage,
  }) => {
    // Precondition: §2.5 completed with the single red T-shirt in the cart.
    await orderFlow.reachOverviewWithFirstItem();
    await checkoutOverviewPage.expectLoaded();

    // One line item.
    await checkoutOverviewPage.expectSingleLineItem(FIRST_ITEM.name, FIRST_ITEM.price);

    // Payment and shipping strings are TTACart's own.
    await checkoutOverviewPage.expectPaymentAndShipping();

    // Price total block: 8% tax on $15.99 rounds to $1.28, giving $17.27.
    await checkoutOverviewPage.expectTotals(ORDER_TOTALS);

    // Cancel and Finish are both offered; the badge still reads 1.
    await expect(checkoutOverviewPage.cancelLink).toBeVisible();
    await expect(checkoutOverviewPage.finishButton).toBeVisible();
    await checkoutOverviewPage.expectCartBadgeCount('1');
  });

  // ------------------------------------------------------------------- §2.7
  test('Finish reaches the confirmation page', async ({
    orderFlow,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    // Precondition: on checkout step two with one item.
    await orderFlow.reachOverviewWithFirstItem();

    // 1. Click Finish.
    await checkoutOverviewPage.finish();

    await checkoutCompletePage.expectLoaded();
    await expect(checkoutCompletePage.pageHeading).toHaveText(
      HEADINGS.checkoutComplete,
    );
    await expect(checkoutCompletePage.container).toBeVisible();
    await checkoutCompletePage.expectOrderConfirmed();
    await expect(checkoutCompletePage.ponyExpress).toBeVisible();

    // The cart is emptied by finishing, so the badge leaves the DOM (§6.4).
    await checkoutCompletePage.expectCartBadgeAbsent();
  });
});
