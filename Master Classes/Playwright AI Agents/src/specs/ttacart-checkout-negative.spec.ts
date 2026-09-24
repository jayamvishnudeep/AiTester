// spec: specs/ttacart-e2e-order-plan.md §4
// seed: src/seed.spec.ts
//
// Every test below depends on checkout step one being genuinely blank when it
// arrives. TTACart pre-fills that form from localStorage and does not clear the
// key when an order completes (plan §6.3), so the reset lives in the
// cleanSession fixture in src/fixtures/tta-test.ts. Remove it and §4.1 – §4.4
// submit leftover values and pass without testing anything.

import { expect, test } from '../fixtures/tta-test';
import {
  CUSTOMER,
  EMPTY_ORDER_TOTALS,
  ERRORS,
  FIRST_ITEM,
  HEADINGS,
  NON_NUMERIC_POSTAL_CODE,
  ORDER_TOTALS,
  WHITESPACE,
} from '../fixtures/test-data';

test.describe('TTACart — negative cases: cart and checkout', () => {
  // ------------------------------------------------------------------- §4.1
  test('First Name left blank is rejected', async ({
    orderFlow,
    checkoutInformationPage,
  }) => {
    await orderFlow.reachCheckoutStepOne();

    // 1-2. Leave First Name blank, fill the other two fields.
    await checkoutInformationPage.fillDetails(
      '',
      CUSTOMER.lastName,
      CUSTOMER.postalCode,
    );

    // 3. Click Continue.
    await checkoutInformationPage.continue();

    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.firstNameRequired);

    // The values already entered are retained.
    await expect(checkoutInformationPage.lastNameInput).toHaveValue(
      CUSTOMER.lastName,
    );
    await expect(checkoutInformationPage.postalCodeInput).toHaveValue(
      CUSTOMER.postalCode,
    );
  });

  // ------------------------------------------------------------------- §4.2
  test('Last Name left blank is rejected', async ({
    orderFlow,
    checkoutInformationPage,
  }) => {
    await orderFlow.reachCheckoutStepOne();

    // 1. First Name John, Last Name blank, Postal Code 12345.
    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      '',
      CUSTOMER.postalCode,
    );

    // 2. Click Continue.
    await checkoutInformationPage.continue();

    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.lastNameRequired);
  });

  // ------------------------------------------------------------------- §4.3
  test('Zip/Postal Code left blank is rejected', async ({
    orderFlow,
    checkoutInformationPage,
  }) => {
    await orderFlow.reachCheckoutStepOne();

    // 1. First Name John, Last Name Doe, Postal Code blank.
    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      CUSTOMER.lastName,
      '',
    );

    // 2. Click Continue.
    await checkoutInformationPage.continue();

    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.postalCodeRequired);
  });

  // ------------------------------------------------------------------- §4.4
  test('Whitespace-only field values are treated as blank', async ({
    orderFlow,
    checkoutInformationPage,
  }) => {
    await orderFlow.reachCheckoutStepOne();

    // 1-3. Three spaces in First Name, valid Last Name and Postal Code.
    await checkoutInformationPage.fillDetails(
      WHITESPACE,
      CUSTOMER.lastName,
      CUSTOMER.postalCode,
    );
    await checkoutInformationPage.continue();

    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.firstNameRequired);
    // The value is trimmed before validation; the field is not cleared.
    await expect(checkoutInformationPage.firstNameInput).toHaveValue(WHITESPACE);

    // The same holds for a whitespace-only Last Name.
    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      WHITESPACE,
      CUSTOMER.postalCode,
    );
    await checkoutInformationPage.continue();
    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.lastNameRequired);
    await expect(checkoutInformationPage.lastNameInput).toHaveValue(WHITESPACE);

    // And for a whitespace-only Postal Code.
    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      CUSTOMER.lastName,
      WHITESPACE,
    );
    await checkoutInformationPage.continue();
    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.postalCodeRequired);
    await expect(checkoutInformationPage.postalCodeInput).toHaveValue(WHITESPACE);
  });

  // ------------------------------------------------------------------- §4.5
  test('Cancel on the checkout information step returns to the cart', async ({
    orderFlow,
    checkoutInformationPage,
    cartPage,
  }) => {
    await orderFlow.reachCheckoutStepOne();

    // 1. Click Cancel (an anchor, not a button).
    await checkoutInformationPage.cancel();

    await cartPage.expectAtUrl();
    // Nothing is discarded.
    await expect(cartPage.lineItems).toHaveCount(1);
    await expect(cartPage.itemName).toHaveText(FIRST_ITEM.name);
    await cartPage.expectCartBadgeCount('1');
  });

  // ------------------------------------------------------------------- §4.6
  test('Cancel on the overview step returns to the cart', async ({
    orderFlow,
    checkoutOverviewPage,
    cartPage,
    checkoutCompletePage,
  }) => {
    // 1. Complete step one with valid details to reach the overview.
    await orderFlow.reachOverviewWithFirstItem();

    // 2. Click Cancel. TTACart's overview Cancel goes to the cart, not the
    //    products page as on saucedemo.com.
    await checkoutOverviewPage.cancel();

    await cartPage.expectAtUrl();
    await expect(cartPage.lineItems).toHaveCount(1);
    await cartPage.expectCartBadgeCount('1');
    // The order was not placed.
    await expect(checkoutCompletePage.header).toHaveCount(0);
  });

  // ------------------------------------------------------------------- §4.7
  // PINS A SUSPECTED BUG (plan §6.2): there is no length, character or numeric
  // constraint on the postal code — only "non-empty after trimming". This test
  // asserts the CURRENT behaviour so that tightening the validation fails
  // loudly and is updated on purpose. It is not an endorsement.
  test('A non-numeric postal code is accepted (pins suspected bug §6.2)', async ({
    orderFlow,
    checkoutInformationPage,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    await orderFlow.reachCheckoutStepOne();

    // 1-2. Valid names, a nonsense postal code.
    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      CUSTOMER.lastName,
      NON_NUMERIC_POSTAL_CODE,
    );

    // 3. Click Continue.
    await checkoutInformationPage.continue();

    // No error is raised and the overview is reached.
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.pageHeading).toHaveText(HEADINGS.checkoutStepTwo);
    await expect(checkoutOverviewPage.totalLabel).toHaveText(ORDER_TOTALS.total);

    // The order can be finished normally.
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await checkoutCompletePage.expectConfirmationHeader();
  });

  // ------------------------------------------------------------------- §4.8
  // PINS A SUSPECTED BUG (plan §6.1): an empty cart can be checked out to a
  // completed $0.00 order. A storefront should not confirm an order with
  // nothing in it. This test asserts the CURRENT observed behaviour so that
  // when the application starts blocking empty-cart checkout it fails loudly
  // and is updated deliberately. Passing here is not approval.
  test('Checking out with an empty cart completes a $0.00 order (pins suspected bug §6.1)', async ({
    orderFlow,
    cartPage,
    checkoutInformationPage,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    // 1. Log in and add nothing. 2. Confirm the empty-cart message.
    await orderFlow.reachEmptyCart();
    await cartPage.expectEmpty();

    // 3. Click Checkout — still offered, and still opens step one.
    await cartPage.checkout();
    await checkoutInformationPage.expectAtUrl();

    // 4. Enter valid details and click Continue.
    await checkoutInformationPage.fillValidDetails();
    await checkoutInformationPage.continue();

    // The overview renders no line items and a zero total.
    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.lineItems).toHaveCount(0);
    await checkoutOverviewPage.expectTotals(EMPTY_ORDER_TOTALS);

    // 5. Click Finish — the order for nothing is confirmed.
    await checkoutOverviewPage.finish();
    await checkoutCompletePage.expectAtUrl();
    await checkoutCompletePage.expectConfirmationHeader();
  });
});
