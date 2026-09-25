// spec: specs/ttacart-e2e-order-plan.md §1
//
// Every verified value the suite asserts against. All of it was read off the
// running application by the playwright-test-planner agent and confirmed again
// by the generator agent as it wrote each test — none of it is inferred.
//
// Assertions copied from a saucedemo.com suite will not work here. TTACart's
// catalogue, prices, payment card name and courier string are its own; the plan
// calls out each divergence inline (§1.3).

import { APP_URL } from '../config/credentials';

export { APP_URL };

/**
 * The URLs the browser actually reports.
 *
 * The in-page links target `./inventory.html` and friends, but the server serves
 * them without the extension, so every URL assertion uses the extension-less
 * form (plan §1.1).
 */
export const URLS = {
  login: APP_URL,
  inventory: `${APP_URL}inventory`,
  cart: `${APP_URL}cart`,
  checkoutStepOne: `${APP_URL}checkout-step-one`,
  checkoutStepTwo: `${APP_URL}checkout-step-two`,
  checkoutComplete: `${APP_URL}checkout-complete`,
} as const;

/** `document.title` per page (plan §1.1). */
export const TITLES = {
  login: 'TTACart - Login',
  inventory: 'TTACart - Products',
  cart: 'TTACart - Your Cart',
  checkoutStepOne: 'TTACart - Checkout: Your Information',
  checkoutStepTwo: 'TTACart - Checkout: Overview',
  checkoutComplete: 'TTACart - Checkout: Complete!',
} as const;

/** The `[data-test="title"]` heading each signed-in page renders (plan §1.1). */
export const HEADINGS = {
  inventory: 'Products',
  cart: 'Your Cart',
  checkoutStepOne: 'Checkout: Your Information',
  checkoutStepTwo: 'Checkout: Overview',
  checkoutComplete: 'Checkout: Complete!',
} as const;

/**
 * The first card under the default Name (A to Z) sort — and NOT one of the five
 * `TTA …` products: the locale comparison puts `Te` before `TT`, so the red
 * T-shirt sorts first (plan §1.3).
 */
export const FIRST_ITEM = {
  id: 'test-allthethings-tshirt-red',
  name: 'Test.allTheThings() T-Shirt (Red)',
  price: '$15.99',
} as const;

/** The first card under Name (Z to A) (addendum §8.4). */
export const LAST_ITEM_ALPHABETICALLY = 'TTA Practice Backpack';

/** The whole catalogue is six cards. */
export const INVENTORY_COUNT = 6;

/** The four verified sort values (addendum §8.4). */
export const SORT_OPTIONS = {
  nameAsc: 'az',
  nameDesc: 'za',
  priceAsc: 'lohi',
  priceDesc: 'hilo',
} as const;

/** Overview totals for a single red T-shirt: 8% tax on $15.99 (plan §1.3). */
export const ORDER_TOTALS = {
  subtotal: 'Item total: $15.99',
  tax: 'Tax: $1.28',
  total: 'Total: $17.27',
} as const;

/** Overview totals with an empty cart — see the pinned bug in plan §6.1. */
export const EMPTY_ORDER_TOTALS = {
  subtotal: 'Item total: $0.00',
  tax: 'Tax: $0.00',
  total: 'Total: $0.00',
} as const;

/** Payment and shipping strings are TTACart's own, not saucedemo's. */
export const ORDER_DETAILS = {
  payment: 'TTACard #31337',
  shipping: 'Free TTA Express Delivery!',
} as const;

/** Confirmation-page copy (plan §1.1). */
export const CONFIRMATION = {
  header: 'Thank you for your order!',
  text: 'Your order has been dispatched, and will arrive just as fast as the TTA Express pony can get there!',
  backHome: 'Back Home',
} as const;

/** Verbatim banner text (plan §1.4). Never paraphrase these. */
export const ERRORS = {
  /** Wrong password, unknown user, wrong-case username, whitespace password. */
  credentials:
    'Epic sadface: Username and password do not match any user in this service',
  lockedOut: 'Epic sadface: Sorry, this user has been locked out.',
  usernameRequired: 'Epic sadface: Username is required',
  firstNameRequired: 'Error: First Name is required',
  lastNameRequired: 'Error: Last Name is required',
  postalCodeRequired: 'Error: Postal Code is required',
} as const;

export const CART_EMPTY_MESSAGE = 'Your cart is empty.';

/** Valid checkout details for every scenario that must get past step one. */
export const CUSTOMER = {
  firstName: 'John',
  lastName: 'Doe',
  postalCode: '12345',
} as const;

/**
 * Three spaces. Whitespace satisfies the HTML `required` attribute, so it slips
 * past native browser validation and reaches the application's own validator —
 * the only route to the app's "is required" banners (plan §3.6, §4.4).
 */
export const WHITESPACE = '   ';

/** No numeric content. Accepted by the app; pinned, not endorsed (plan §6.2). */
export const NON_NUMERIC_POSTAL_CODE = 'not-a-zip!!';

/** The localStorage keys TTACart writes (plan §6.3, addendum §8.5 – §8.6). */
export const STORAGE_KEYS = {
  user: 'tta-cart-user',
  items: 'tta-cart-items',
  sort: 'tta-cart-sort',
  checkoutInfo: 'tta-cart-checkout-info',
} as const;

/** The saved checkout payload, as the app writes it (addendum §8.3). */
export const SAVED_CHECKOUT_INFO =
  '{"firstName":"John","lastName":"Doe","postal":"12345"}';
