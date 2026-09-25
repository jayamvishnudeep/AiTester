// spec: specs/ttacart-e2e-order-plan.md §2.5, §4.1 – §4.5
// seed: src/tests/seed.spec.ts
//
// Every test here depends on step one being genuinely blank when it arrives.
// TTACart pre-fills that form from localStorage and does not clear the key when
// an order completes (plan §6.3), which is why the reset lives in the
// cleanSession fixture in src/fixtures/test-base.ts.
//
// Worth knowing while reading these: the form validates correctly, and it is
// also OPTIONAL. Checkout step two renders by URL whether or not this page was
// ever visited (addendum §9.2), so these four negatives establish that the fields
// are required — not that the details cannot be skipped.

import { expect, test } from '@fixtures/test-base';
import {
  CUSTOMER,
  ERRORS,
  FIRST_ITEM,
  HEADINGS,
  WHITESPACE,
} from '@testdata/ttacart.data';

test.describe('Checkout — information step', () => {
  // ------------------------------------------------------------------- §2.5
  test('Valid details are accepted and advance to the overview @p0', async ({
    atCheckoutInformation,
    checkoutInformationPage,
    checkoutOverviewPage,
  }) => {
    void atCheckoutInformation;

    await checkoutInformationPage.expectLoaded();
    await expect(checkoutInformationPage.pageHeading).toHaveText(
      HEADINGS.checkoutStepOne,
    );

    // The three fields start empty — true only from a clean context.
    await checkoutInformationPage.expectFieldsEmpty();

    await checkoutInformationPage.fillValidDetails();
    await checkoutInformationPage.continue();

    await checkoutOverviewPage.expectAtUrl();
    await expect(checkoutOverviewPage.pageHeading).toHaveText(
      HEADINGS.checkoutStepTwo,
    );
  });

  // ------------------------------------------------------------------- §4.1
  test('First Name left blank is rejected', async ({
    atCheckoutInformation,
    checkoutInformationPage,
  }) => {
    void atCheckoutInformation;

    await checkoutInformationPage.fillDetails(
      '',
      CUSTOMER.lastName,
      CUSTOMER.postalCode,
    );
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
    atCheckoutInformation,
    checkoutInformationPage,
  }) => {
    void atCheckoutInformation;

    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      '',
      CUSTOMER.postalCode,
    );
    await checkoutInformationPage.continue();

    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.lastNameRequired);
  });

  // ------------------------------------------------------------------- §4.3
  test('Zip/Postal Code left blank is rejected', async ({
    atCheckoutInformation,
    checkoutInformationPage,
  }) => {
    void atCheckoutInformation;

    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      CUSTOMER.lastName,
      '',
    );
    await checkoutInformationPage.continue();

    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.postalCodeRequired);
  });

  // ------------------------------------------------------------------- §4.4
  test('Whitespace-only field values are treated as blank', async ({
    atCheckoutInformation,
    checkoutInformationPage,
  }) => {
    void atCheckoutInformation;

    // Whitespace satisfies the HTML required attribute, so it reaches the app's
    // own validator, which trims before checking.
    await checkoutInformationPage.fillDetails(
      WHITESPACE,
      CUSTOMER.lastName,
      CUSTOMER.postalCode,
    );
    await checkoutInformationPage.continue();
    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.firstNameRequired);
    // Trimmed before validation; the field itself is not cleared.
    await expect(checkoutInformationPage.firstNameInput).toHaveValue(WHITESPACE);

    await checkoutInformationPage.fillDetails(
      CUSTOMER.firstName,
      WHITESPACE,
      CUSTOMER.postalCode,
    );
    await checkoutInformationPage.continue();
    await checkoutInformationPage.expectAtUrl();
    await checkoutInformationPage.expectError(ERRORS.lastNameRequired);
    await expect(checkoutInformationPage.lastNameInput).toHaveValue(WHITESPACE);

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
  test('Cancel returns to the cart without discarding it', async ({
    atCheckoutInformation,
    checkoutInformationPage,
    cartPage,
  }) => {
    void atCheckoutInformation;

    // Cancel is an anchor, not a button (plan §6.5).
    await checkoutInformationPage.cancel();

    await cartPage.expectAtUrl();
    await expect(cartPage.lineItems).toHaveCount(1);
    await expect(cartPage.itemName).toHaveText(FIRST_ITEM.name);
    await cartPage.expectCartBadgeCount('1');
  });
});
