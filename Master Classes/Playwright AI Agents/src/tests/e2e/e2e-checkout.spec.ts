// spec: specs/ttacart-e2e-order-plan.md §2.1
// seed: src/tests/seed.spec.ts
//
// The primary scenario, written out step by step rather than assembled from state
// fixtures. The fixtures are the right tool for a precondition; they are the
// wrong tool here, because the whole journey IS what this test asserts and
// hiding half of it behind a fixture name would hide the thing under test.

import { expect, test } from '@fixtures/test-base';
import { standardUser } from '@config/credentials';
import {
  FIRST_ITEM,
  HEADINGS,
  ORDER_TOTALS,
  TITLES,
} from '@testdata/ttacart.data';
import { visualStep } from '@utils/visualStep';

test.describe('E2E checkout', () => {
  // ------------------------------------------------------------------- §2.1
  test('Full happy path: login, add first item, checkout, confirmation @p0', async ({
    page,
    loginPage,
    inventoryPage,
    cartPage,
    checkoutInformationPage,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    await visualStep(page, '1. Open the login page', async () => {
      await loginPage.goto();
      await expect(page).toHaveTitle(TITLES.login);
      await loginPage.expectNoError();
    });

    await visualStep(page, '2. Sign in as the standard user', async () => {
      await loginPage.loginAs(standardUser.username, standardUser.password);
      await expect(inventoryPage.pageHeading).toHaveText(HEADINGS.inventory);
    });

    await visualStep(page, '3. Add the first item to the cart', async () => {
      await inventoryPage.addFirstItemToCart();
    });

    await visualStep(page, '4. Open the cart', async () => {
      await inventoryPage.openCart();
      await cartPage.expectAtUrl();
      await expect(cartPage.itemName).toHaveText(FIRST_ITEM.name);
    });

    await visualStep(page, '5. Checkout', async () => {
      // Checkout is an anchor, not a button (plan §6.5).
      await cartPage.checkout();
      await checkoutInformationPage.expectAtUrl();
      await checkoutInformationPage.expectNoError();
    });

    await visualStep(page, '6. Enter the customer details and continue', async () => {
      await checkoutInformationPage.fillValidDetails();
      await checkoutInformationPage.continue();
      await checkoutOverviewPage.expectAtUrl();
      await expect(checkoutOverviewPage.pageHeading).toHaveText(
        HEADINGS.checkoutStepTwo,
      );
      await expect(checkoutOverviewPage.totalLabel).toHaveText(ORDER_TOTALS.total);
    });

    await visualStep(page, '7. Finish the order', async () => {
      await checkoutOverviewPage.finish();
      await checkoutCompletePage.expectAtUrl();
      await checkoutCompletePage.expectOrderConfirmed();

      // Finishing empties the cart, and the badge leaves the DOM rather than
      // being hidden (plan §6.4).
      await checkoutCompletePage.expectCartBadgeAbsent();
    });
  });

  // ------------------------------------------------------------------- §2.7
  test('Finish reaches the confirmation page', async ({
    atCheckoutOverview,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    void atCheckoutOverview;

    await checkoutOverviewPage.finish();

    await checkoutCompletePage.expectLoaded();
    await expect(checkoutCompletePage.pageHeading).toHaveText(
      HEADINGS.checkoutComplete,
    );
    await expect(checkoutCompletePage.container).toBeVisible();
    await checkoutCompletePage.expectOrderConfirmed();
    await expect(checkoutCompletePage.ponyExpress).toBeVisible();
    await checkoutCompletePage.expectCartBadgeAbsent();
  });
});
