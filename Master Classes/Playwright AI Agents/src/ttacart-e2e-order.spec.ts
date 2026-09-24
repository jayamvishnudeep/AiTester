// spec: specs/ttacart-e2e-order-plan.md
// seed: src/seed.spec.ts

import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Routes. The in-page links target ./inventory.html etc., but the server serves
// them without the extension, so every URL assertion uses the extension-less
// form the browser actually reports (plan §1.1).
// ---------------------------------------------------------------------------
const APP_URL = 'https://app.thetestingacademy.com/playwright/ttacart/';
const INVENTORY_URL = `${APP_URL}inventory`;
const CART_URL = `${APP_URL}cart`;
const STEP_ONE_URL = `${APP_URL}checkout-step-one`;
const STEP_TWO_URL = `${APP_URL}checkout-step-two`;
const COMPLETE_URL = `${APP_URL}checkout-complete`;

// Credentials come from the environment (.env, loaded by dotenv in
// playwright.config.ts). TTA_-prefixed because Windows defines USERNAME as a
// system variable and dotenv will not overwrite an already-set variable.
const USERNAME = process.env.TTA_USERNAME ?? '';
const PASSWORD = process.env.TTA_PASSWORD ?? '';

// The first card under the default Name (A to Z) sort (plan §1.3).
const FIRST_ITEM_NAME = 'Test.allTheThings() T-Shirt (Red)';
const FIRST_ITEM_PRICE = '$15.99';
const ADD_FIRST_ITEM = '[data-test="add-to-cart-test-allthethings-tshirt-red"]';
const REMOVE_FIRST_ITEM = '[data-test="remove-test-allthethings-tshirt-red"]';

// Shared selectors. Checkout, Cancel and Continue Shopping are anchors, not
// buttons, so getByRole('button') will not find them — plan §6.5.
const CART_LINK = '[data-test="shopping-cart-link"]';
const CART_BADGE = '[data-test="shopping-cart-badge"]';
const CHECKOUT_LINK = '[data-test="checkout"]';
const CANCEL_LINK = '[data-test="cancel"]';
const CONTINUE_BUTTON = '[data-test="continue"]';
const FINISH_BUTTON = '[data-test="finish"]';
const ERROR_BANNER = '[data-test="error"]';
const PAGE_TITLE = '[data-test="title"]';

const CREDENTIALS_ERROR =
  'Epic sadface: Username and password do not match any user in this service';

// ---------------------------------------------------------------------------
// Hazard, plan §6.3: the checkout details are persisted in localStorage under
// tta-cart-checkout-info, step one pre-fills from that key, and the key is NOT
// cleared when an order completes. Without this reset the blank-field negatives
// (§4.1 – §4.4) would submit leftover values and silently pass. page.evaluate is
// used deliberately here: this is fixture teardown of browser storage, for which
// Playwright exposes no API — every assertion below uses real web-first
// expect(locator) assertions.
// ---------------------------------------------------------------------------
test.beforeEach(async ({ page }) => {
  await page.goto(APP_URL);
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
});

async function login(page: Page, username = USERNAME, password = PASSWORD) {
  await page.goto(APP_URL);
  await page.locator('#user-name').fill(username);
  await page.locator('#password').fill(password);
  await page.locator('#login-button').click();
  await expect(page).toHaveURL(INVENTORY_URL);
}

/** Submit the login form without asserting that it succeeded. */
async function attemptLogin(page: Page, username: string, password: string) {
  await page.locator('#user-name').fill(username);
  await page.locator('#password').fill(password);
  await page.locator('#login-button').click();
}

async function addFirstItemToCart(page: Page) {
  await page.locator(ADD_FIRST_ITEM).click();
  // The badge is inserted into the header; it does not merely become visible.
  await expect(page.locator(CART_BADGE)).toHaveText('1');
}

/** Logged in as the standard user, one red T-shirt in the cart, on step one. */
async function reachCheckoutStepOne(page: Page) {
  await login(page);
  await addFirstItemToCart(page);
  await page.locator(CART_LINK).click();
  await expect(page).toHaveURL(CART_URL);
  await page.locator(CHECKOUT_LINK).click();
  await expect(page).toHaveURL(STEP_ONE_URL);
}

async function fillCheckoutDetails(
  page: Page,
  firstName: string,
  lastName: string,
  postalCode: string,
) {
  await page.locator('#first-name').fill(firstName);
  await page.locator('#last-name').fill(lastName);
  await page.locator('#postal-code').fill(postalCode);
}

// ===========================================================================
test.describe('TTACart — positive cases', () => {
  // ------------------------------------------------------------------ §2.1
  test('Full happy path: login, add first item, checkout, confirmation', async ({ page }) => {
    // 1. Navigate to the login page.
    await page.goto(APP_URL);
    await expect(page).toHaveTitle('TTACart - Login');
    await expect(page.locator(ERROR_BANNER)).toHaveText('');

    // 2-4. Enter the credentials and click Login.
    await page.locator('#user-name').fill(USERNAME);
    await page.locator('#password').fill(PASSWORD);
    await page.locator('#login-button').click();
    await expect(page).toHaveURL(INVENTORY_URL);
    await expect(page.locator(PAGE_TITLE)).toHaveText('Products');

    // 5. Add the first inventory card to the cart.
    await page.locator(ADD_FIRST_ITEM).click();
    await expect(page.locator(CART_BADGE)).toHaveText('1');

    // 6. Open the cart from the header.
    await page.locator(CART_LINK).click();
    await expect(page).toHaveURL(CART_URL);
    await expect(page.locator('[data-test="inventory-item-name"]')).toHaveText(FIRST_ITEM_NAME);

    // 7. Click Checkout (an anchor, not a button).
    await page.locator(CHECKOUT_LINK).click();
    await expect(page).toHaveURL(STEP_ONE_URL);
    await expect(page.locator(ERROR_BANNER)).toHaveText('');

    // 8. Enter the customer details.
    await fillCheckoutDetails(page, 'John', 'Doe', '12345');

    // 9. Click Continue.
    await page.locator(CONTINUE_BUTTON).click();
    await expect(page).toHaveURL(STEP_TWO_URL);
    await expect(page.locator(PAGE_TITLE)).toHaveText('Checkout: Overview');
    await expect(page.locator('[data-test="total-label"]')).toHaveText('Total: $17.27');

    // 10. Click Finish.
    await page.locator(FINISH_BUTTON).click();
    await expect(page).toHaveURL(COMPLETE_URL);
    await expect(page.locator('[data-test="complete-header"]')).toHaveText(
      'Thank you for your order!',
    );
    await expect(page.locator('[data-test="complete-text"]')).toHaveText(
      'Your order has been dispatched, and will arrive just as fast as the TTA Express pony can get there!',
    );
    await expect(page.locator('[data-test="back-to-products"]')).toHaveText('Back Home');
    // Finishing empties the cart, and the badge is removed from the DOM
    // rather than hidden — plan §6.4.
    await expect(page.locator(CART_BADGE)).toHaveCount(0);
  });

  // ------------------------------------------------------------------ §2.2
  test('Successful login lands on the products page', async ({ page }) => {
    // 1-2. Navigate to the login page, sign in as the standard user.
    await page.goto(APP_URL);
    await page.locator('#user-name').fill(USERNAME);
    await page.locator('#password').fill(PASSWORD);
    await page.locator('#login-button').click();

    await expect(page).toHaveURL(INVENTORY_URL);
    await expect(page).toHaveTitle('TTACart - Products');
    await expect(page.locator(PAGE_TITLE)).toHaveText('Products');

    // Exactly six inventory cards, default A-to-Z sort, red T-shirt first.
    await expect(page.locator('.inventory-item')).toHaveCount(6);
    const sort = page.locator('#product-sort-container');
    await expect(sort).toHaveValue('az');
    await expect(sort.locator('option[value="az"]')).toHaveText('Name (A to Z)');
    await expect(page.locator('[data-test="inventory-item-name"]').first()).toHaveText(
      FIRST_ITEM_NAME,
    );
    await expect(page.locator('[data-test="inventory-item-price"]').first()).toHaveText(
      FIRST_ITEM_PRICE,
    );

    // Header exposes the burger menu and the cart link, and no badge because
    // the cart is empty (absent from the DOM, not hidden — plan §6.4).
    await expect(page.locator('[data-test="primary-header"]')).toBeVisible();
    await expect(page.locator('[data-test="open-menu"]')).toBeVisible();
    await expect(page.locator(CART_LINK)).toBeVisible();
    await expect(page.locator(CART_BADGE)).toHaveCount(0);
  });

  // ------------------------------------------------------------------ §2.3
  test('Cart badge updates when the first item is added', async ({ page }) => {
    // 1. Log in as the standard user.
    await login(page);
    await expect(page.locator(CART_BADGE)).toHaveCount(0);

    // 2. Click Add to cart on the first inventory card.
    await page.locator(ADD_FIRST_ITEM).click();

    await expect(page.locator(CART_BADGE)).toHaveText('1');
    // The button re-renders as Remove; its data-test attribute flips too.
    const removeButton = page.locator(REMOVE_FIRST_ITEM);
    await expect(removeButton).toHaveText('Remove');
    await expect(removeButton).toHaveClass('item-btn is-remove');
    await expect(page.locator(ADD_FIRST_ITEM)).toHaveCount(0);
    // No navigation.
    await expect(page).toHaveURL(INVENTORY_URL);
  });

  // ------------------------------------------------------------------ §2.4
  test('Cart page shows the correct line item', async ({ page }) => {
    // 1. Log in as the standard user and add the first item.
    await login(page);
    await addFirstItemToCart(page);

    // 2. Click the cart link in the header.
    await page.locator(CART_LINK).click();

    await expect(page).toHaveURL(CART_URL);
    await expect(page).toHaveTitle('TTACart - Your Cart');
    await expect(page.locator(PAGE_TITLE)).toHaveText('Your Cart');

    const rows = page.locator('[data-test="inventory-item"]');
    await expect(rows).toHaveCount(1);
    await expect(page.locator('[data-test="inventory-item-name"]')).toHaveText(FIRST_ITEM_NAME);
    await expect(page.locator('[data-test="inventory-item-price"]')).toHaveText(FIRST_ITEM_PRICE);
    await expect(page.locator('[data-test="item-quantity"]')).toHaveText('1');
    await expect(page.locator(CART_BADGE)).toHaveText('1');

    await expect(page.locator(REMOVE_FIRST_ITEM)).toBeVisible();
    await expect(page.locator('[data-test="continue-shopping"]')).toHaveAttribute(
      'href',
      './inventory.html',
    );
    await expect(page.locator(CHECKOUT_LINK)).toHaveAttribute(
      'href',
      './checkout-step-one.html',
    );
  });

  // ------------------------------------------------------------------ §2.5
  test('Checkout information form accepts valid details and advances', async ({ page }) => {
    // 1. Reach checkout step one with one item in the cart.
    await reachCheckoutStepOne(page);
    await expect(page).toHaveTitle('TTACart - Checkout: Your Information');
    await expect(page.locator(PAGE_TITLE)).toHaveText('Checkout: Your Information');

    // 2. Confirm the three fields start empty (true only from a clean context).
    await expect(page.locator('#first-name')).toHaveValue('');
    await expect(page.locator('#last-name')).toHaveValue('');
    await expect(page.locator('#postal-code')).toHaveValue('');

    // 3. Enter the customer details.
    await fillCheckoutDetails(page, 'John', 'Doe', '12345');

    // 4. Click Continue.
    await page.locator(CONTINUE_BUTTON).click();

    // No error banner, and the browser advances to the overview.
    await expect(page).toHaveURL(STEP_TWO_URL);
    await expect(page.locator(PAGE_TITLE)).toHaveText('Checkout: Overview');
  });

  // ------------------------------------------------------------------ §2.6
  test('Overview page shows a correct order summary', async ({ page }) => {
    // Precondition: §2.5 completed with the single red T-shirt in the cart.
    await reachCheckoutStepOne(page);
    await fillCheckoutDetails(page, 'John', 'Doe', '12345');
    await page.locator(CONTINUE_BUTTON).click();
    await expect(page).toHaveURL(STEP_TWO_URL);
    await expect(page).toHaveTitle('TTACart - Checkout: Overview');

    // One line item.
    await expect(page.locator('[data-test="inventory-item"]')).toHaveCount(1);
    await expect(page.locator('[data-test="inventory-item-name"]')).toHaveText(FIRST_ITEM_NAME);
    await expect(page.locator('[data-test="inventory-item-price"]')).toHaveText(FIRST_ITEM_PRICE);
    await expect(page.locator('[data-test="item-quantity"]')).toHaveText('1');

    // Payment and shipping strings are TTACart's own.
    await expect(page.locator('[data-test="payment-info-value"]')).toHaveText('TTACard #31337');
    await expect(page.locator('[data-test="shipping-info-value"]')).toHaveText(
      'Free TTA Express Delivery!',
    );

    // Price total block: 8% tax on $15.99 rounds to $1.28, giving $17.27.
    await expect(page.locator('[data-test="subtotal-label"]')).toHaveText('Item total: $15.99');
    await expect(page.locator('[data-test="tax-label"]')).toHaveText('Tax: $1.28');
    await expect(page.locator('[data-test="total-label"]')).toHaveText('Total: $17.27');

    // Cancel and Finish are both offered; the badge still reads 1.
    await expect(page.locator(CANCEL_LINK)).toBeVisible();
    await expect(page.locator(FINISH_BUTTON)).toBeVisible();
    await expect(page.locator(CART_BADGE)).toHaveText('1');
  });

  // ------------------------------------------------------------------ §2.7
  test('Finish reaches the confirmation page', async ({ page }) => {
    // Precondition: on checkout step two with one item.
    await reachCheckoutStepOne(page);
    await fillCheckoutDetails(page, 'John', 'Doe', '12345');
    await page.locator(CONTINUE_BUTTON).click();
    await expect(page).toHaveURL(STEP_TWO_URL);

    // 1. Click Finish.
    await page.locator(FINISH_BUTTON).click();

    await expect(page).toHaveURL(COMPLETE_URL);
    await expect(page).toHaveTitle('TTACart - Checkout: Complete!');
    await expect(page.locator(PAGE_TITLE)).toHaveText('Checkout: Complete!');
    await expect(page.locator('[data-test="checkout-complete-container"]')).toBeVisible();
    await expect(page.locator('[data-test="complete-header"]')).toHaveText(
      'Thank you for your order!',
    );
    await expect(page.locator('[data-test="complete-text"]')).toHaveText(
      'Your order has been dispatched, and will arrive just as fast as the TTA Express pony can get there!',
    );
    await expect(page.locator('[data-test="pony-express"]')).toBeVisible();
    await expect(page.locator('[data-test="back-to-products"]')).toHaveText('Back Home');
    // The cart is emptied by finishing, so the badge leaves the DOM (§6.4).
    await expect(page.locator(CART_BADGE)).toHaveCount(0);
  });
});

// ===========================================================================
test.describe('TTACart — negative cases: login', () => {
  // ------------------------------------------------------------------ §3.1
  test('Invalid password is refused', async ({ page }) => {
    // 1-4. On the login page, enter the valid username with a wrong password.
    await attemptLogin(page, USERNAME, 'wrong_password');

    await expect(page).toHaveURL(APP_URL);
    await expect(page.locator(ERROR_BANNER)).toHaveText(CREDENTIALS_ERROR);
    await expect(page.locator(ERROR_BANNER)).toHaveAttribute('role', 'alert');
    // No session: the products page is still unreachable by deep link.
    await page.goto(INVENTORY_URL);
    await expect(page).toHaveURL(APP_URL);
  });

  // ------------------------------------------------------------------ §3.2
  test('Locked-out user cannot log in', async ({ page }) => {
    // 1-3. Enter locked_out_user with the valid password and submit.
    await attemptLogin(page, 'locked_out_user', PASSWORD);

    await expect(page).toHaveURL(APP_URL);
    await expect(page.locator(ERROR_BANNER)).toHaveText(
      'Epic sadface: Sorry, this user has been locked out.',
    );
    // No session was written, so the products page cannot be deep-linked.
    await page.goto(INVENTORY_URL);
    await expect(page).toHaveURL(APP_URL);
    await expect(page).toHaveTitle('TTACart - Login');
  });

  // ------------------------------------------------------------------ §3.3
  test('Unknown username gets the same message as a bad password', async ({ page }) => {
    // 1-3. Enter an unknown username with the valid password and submit.
    await attemptLogin(page, 'nonexistent_user', PASSWORD);

    await expect(page).toHaveURL(APP_URL);
    // Identical to §3.1 — the app does not distinguish the two cases.
    await expect(page.locator(ERROR_BANNER)).toHaveText(CREDENTIALS_ERROR);
  });

  // ------------------------------------------------------------------ §3.4
  test('Empty username is blocked by native browser validation', async ({ page }) => {
    // 1-4. Leave the username blank, enter the password, click Login.
    const username = page.locator('#user-name');
    await page.locator('#password').fill(PASSWORD);
    await page.locator('#login-button').click();

    // The submit never reaches the application: the input carries the HTML
    // required attribute, so Chromium intercepts it. Assert valueMissing
    // rather than any banner text — the app's own "Username is required"
    // branch is unreachable this way (see §3.6 for the only route to it).
    await expect(username).toHaveJSProperty('validity.valueMissing', true);
    await expect(page.locator(ERROR_BANNER)).toHaveText('');
    await expect(page).toHaveURL(APP_URL);
  });

  // ------------------------------------------------------------------ §3.5
  test('Empty password is blocked by native browser validation', async ({ page }) => {
    // 1-4. Enter the username, leave the password blank, click Login.
    const password = page.locator('#password');
    await page.locator('#user-name').fill(USERNAME);
    await page.locator('#login-button').click();

    await expect(password).toHaveJSProperty('validity.valueMissing', true);
    await expect(page.locator(ERROR_BANNER)).toHaveText('');
    await expect(page).toHaveURL(APP_URL);
  });

  // ------------------------------------------------------------------ §3.6
  test('Whitespace-only username reports that the username is required', async ({ page }) => {
    // 1-4. Three spaces satisfy native validation, so the app's own validator
    // runs and trims the value. This is the only route to this message.
    await attemptLogin(page, '   ', PASSWORD);

    await expect(page).toHaveURL(APP_URL);
    await expect(page.locator(ERROR_BANNER)).toHaveText('Epic sadface: Username is required');
  });

  // ------------------------------------------------------------------ §3.7
  test('Whitespace-only password is treated as a wrong password', async ({ page }) => {
    // 1-4. The password is not trimmed, so spaces are a genuine wrong password.
    await attemptLogin(page, USERNAME, '   ');

    await expect(page).toHaveURL(APP_URL);
    // Not a "required" message.
    await expect(page.locator(ERROR_BANNER)).toHaveText(CREDENTIALS_ERROR);
    await expect(page.locator('#password')).toHaveValue('   ');
  });

  // ------------------------------------------------------------------ §3.8
  test('Username matching is case-sensitive', async ({ page }) => {
    // 1-3. Enter the username in the wrong case with the valid password.
    await attemptLogin(page, 'Standard_User', PASSWORD);

    await expect(page).toHaveURL(APP_URL);
    await expect(page.locator(ERROR_BANNER)).toHaveText(CREDENTIALS_ERROR);
  });

  // ------------------------------------------------------------------ §3.9
  test('Checkout pages are not reachable while logged out', async ({ page }) => {
    // 1. Site storage was cleared in beforeEach, so no session exists.
    // 2. Request checkout step one directly.
    await page.goto(STEP_ONE_URL);
    await expect(page).toHaveURL(APP_URL);
    await expect(page).toHaveTitle('TTACart - Login');
    await expect(page.locator('[data-test="login-container"]')).toBeVisible();

    // The same guard protects every other step of the order flow.
    for (const guarded of [INVENTORY_URL, CART_URL, STEP_TWO_URL, COMPLETE_URL]) {
      await page.goto(guarded);
      await expect(page).toHaveURL(APP_URL);
      await expect(page).toHaveTitle('TTACart - Login');
    }
  });
});

// ===========================================================================
test.describe('TTACart — negative cases: cart and checkout', () => {
  // ------------------------------------------------------------------ §4.1
  test('First Name left blank is rejected', async ({ page }) => {
    await reachCheckoutStepOne(page);

    // 1-2. Leave First Name blank, fill the other two fields.
    await fillCheckoutDetails(page, '', 'Doe', '12345');

    // 3. Click Continue.
    await page.locator(CONTINUE_BUTTON).click();

    await expect(page).toHaveURL(STEP_ONE_URL);
    await expect(page.locator(ERROR_BANNER)).toHaveText('Error: First Name is required');
    // The values already entered are retained.
    await expect(page.locator('#last-name')).toHaveValue('Doe');
    await expect(page.locator('#postal-code')).toHaveValue('12345');
  });

  // ------------------------------------------------------------------ §4.2
  test('Last Name left blank is rejected', async ({ page }) => {
    await reachCheckoutStepOne(page);

    // 1. First Name John, Last Name blank, Postal Code 12345.
    await fillCheckoutDetails(page, 'John', '', '12345');

    // 2. Click Continue.
    await page.locator(CONTINUE_BUTTON).click();

    await expect(page).toHaveURL(STEP_ONE_URL);
    await expect(page.locator(ERROR_BANNER)).toHaveText('Error: Last Name is required');
  });

  // ------------------------------------------------------------------ §4.3
  test('Zip/Postal Code left blank is rejected', async ({ page }) => {
    await reachCheckoutStepOne(page);

    // 1. First Name John, Last Name Doe, Postal Code blank.
    await fillCheckoutDetails(page, 'John', 'Doe', '');

    // 2. Click Continue.
    await page.locator(CONTINUE_BUTTON).click();

    await expect(page).toHaveURL(STEP_ONE_URL);
    await expect(page.locator(ERROR_BANNER)).toHaveText('Error: Postal Code is required');
  });

  // ------------------------------------------------------------------ §4.4
  test('Whitespace-only field values are treated as blank', async ({ page }) => {
    await reachCheckoutStepOne(page);
    const banner = page.locator(ERROR_BANNER);

    // 1-3. Three spaces in First Name, valid Last Name and Postal Code.
    await fillCheckoutDetails(page, '   ', 'Doe', '12345');
    await page.locator(CONTINUE_BUTTON).click();

    await expect(page).toHaveURL(STEP_ONE_URL);
    await expect(banner).toHaveText('Error: First Name is required');
    // The value is trimmed before validation; the field is not cleared.
    await expect(page.locator('#first-name')).toHaveValue('   ');

    // The same holds for a whitespace-only Last Name.
    await fillCheckoutDetails(page, 'John', '   ', '12345');
    await page.locator(CONTINUE_BUTTON).click();
    await expect(page).toHaveURL(STEP_ONE_URL);
    await expect(banner).toHaveText('Error: Last Name is required');
    await expect(page.locator('#last-name')).toHaveValue('   ');

    // And for a whitespace-only Postal Code.
    await fillCheckoutDetails(page, 'John', 'Doe', '   ');
    await page.locator(CONTINUE_BUTTON).click();
    await expect(page).toHaveURL(STEP_ONE_URL);
    await expect(banner).toHaveText('Error: Postal Code is required');
    await expect(page.locator('#postal-code')).toHaveValue('   ');
  });

  // ------------------------------------------------------------------ §4.5
  test('Cancel on the checkout information step returns to the cart', async ({ page }) => {
    await reachCheckoutStepOne(page);

    // 1. Click Cancel (an anchor, not a button).
    await page.locator(CANCEL_LINK).click();

    await expect(page).toHaveURL(CART_URL);
    // Nothing is discarded.
    await expect(page.locator('[data-test="inventory-item"]')).toHaveCount(1);
    await expect(page.locator('[data-test="inventory-item-name"]')).toHaveText(FIRST_ITEM_NAME);
    await expect(page.locator(CART_BADGE)).toHaveText('1');
  });

  // ------------------------------------------------------------------ §4.6
  test('Cancel on the overview step returns to the cart', async ({ page }) => {
    // 1. Complete step one with valid details to reach the overview.
    await reachCheckoutStepOne(page);
    await fillCheckoutDetails(page, 'John', 'Doe', '12345');
    await page.locator(CONTINUE_BUTTON).click();
    await expect(page).toHaveURL(STEP_TWO_URL);

    // 2. Click Cancel. TTACart's overview Cancel goes to the cart, not the
    //    products page as on saucedemo.com.
    await page.locator(CANCEL_LINK).click();

    await expect(page).toHaveURL(CART_URL);
    await expect(page.locator('[data-test="inventory-item"]')).toHaveCount(1);
    await expect(page.locator(CART_BADGE)).toHaveText('1');
    // The order was not placed.
    await expect(page.locator('[data-test="complete-header"]')).toHaveCount(0);
  });

  // ------------------------------------------------------------------ §4.7
  // PINS A SUSPECTED BUG (plan §6.2): there is no length, character or numeric
  // constraint on the postal code — only "non-empty after trimming". This test
  // asserts the CURRENT behaviour so that tightening the validation fails
  // loudly and is updated on purpose. It is not an endorsement.
  test('A non-numeric postal code is accepted (pins suspected bug §6.2)', async ({ page }) => {
    await reachCheckoutStepOne(page);

    // 1-2. Valid names, a nonsense postal code.
    await fillCheckoutDetails(page, 'John', 'Doe', 'not-a-zip!!');

    // 3. Click Continue.
    await page.locator(CONTINUE_BUTTON).click();

    // No error is raised and the overview is reached.
    await expect(page).toHaveURL(STEP_TWO_URL);
    await expect(page.locator(PAGE_TITLE)).toHaveText('Checkout: Overview');
    await expect(page.locator('[data-test="total-label"]')).toHaveText('Total: $17.27');

    // The order can be finished normally.
    await page.locator(FINISH_BUTTON).click();
    await expect(page).toHaveURL(COMPLETE_URL);
    await expect(page.locator('[data-test="complete-header"]')).toHaveText(
      'Thank you for your order!',
    );
  });

  // ------------------------------------------------------------------ §4.8
  // PINS A SUSPECTED BUG (plan §6.1): an empty cart can be checked out to a
  // completed $0.00 order. A storefront should not confirm an order with
  // nothing in it. This test asserts the CURRENT observed behaviour so that
  // when the application starts blocking empty-cart checkout it fails loudly
  // and is updated deliberately. Passing here is not approval.
  test('Checking out with an empty cart completes a $0.00 order (pins suspected bug §6.1)', async ({
    page,
  }) => {
    // 1. Log in and add nothing.
    await login(page);
    await expect(page.locator(CART_BADGE)).toHaveCount(0);
    await page.locator(CART_LINK).click();
    await expect(page).toHaveURL(CART_URL);

    // 2. Confirm the empty-cart message.
    await expect(page.locator('[data-test="cart-empty"]')).toHaveText('Your cart is empty.');
    await expect(page.locator('[data-test="inventory-item"]')).toHaveCount(0);

    // 3. Click Checkout — still offered, and still opens step one.
    await page.locator(CHECKOUT_LINK).click();
    await expect(page).toHaveURL(STEP_ONE_URL);

    // 4. Enter valid details and click Continue.
    await fillCheckoutDetails(page, 'John', 'Doe', '12345');
    await page.locator(CONTINUE_BUTTON).click();

    // The overview renders no line items and a zero total.
    await expect(page).toHaveURL(STEP_TWO_URL);
    await expect(page.locator('[data-test="inventory-item"]')).toHaveCount(0);
    await expect(page.locator('[data-test="subtotal-label"]')).toHaveText('Item total: $0.00');
    await expect(page.locator('[data-test="tax-label"]')).toHaveText('Tax: $0.00');
    await expect(page.locator('[data-test="total-label"]')).toHaveText('Total: $0.00');

    // 5. Click Finish — the order for nothing is confirmed.
    await page.locator(FINISH_BUTTON).click();
    await expect(page).toHaveURL(COMPLETE_URL);
    await expect(page.locator('[data-test="complete-header"]')).toHaveText(
      'Thank you for your order!',
    );
  });
});
