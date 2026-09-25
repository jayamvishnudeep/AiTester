// spec: specs/ttacart-e2e-order-plan.md
//
// Every value here was verified live against the deployed application and is
// recorded in §1 of the plan. Nothing in this file is assumed: the prices, the
// tax figure, the payment and courier strings and the exact error text were all
// read off the running page. Assertions copied from a saucedemo.com suite will
// not work — TTACart's catalogue and strings are its own (plan §1.3).

/** The application root. Always absolute — this project does not use baseURL. */
export const APP_URL = 'https://app.thetestingacademy.com/playwright/ttacart/';

/**
 * The in-page links target `./inventory.html` and friends, but the server
 * serves them without the extension. These are the URLs the browser actually
 * reports, which is what every assertion compares against (plan §1.1).
 */
export const URLS = {
  login: APP_URL,
  inventory: `${APP_URL}inventory`,
  cart: `${APP_URL}cart`,
  checkoutStepOne: `${APP_URL}checkout-step-one`,
  checkoutStepTwo: `${APP_URL}checkout-step-two`,
  checkoutComplete: `${APP_URL}checkout-complete`,
} as const;

/** `document.title` for each page (plan §1.1). */
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
 * Credentials come from .env via dotenv, loaded in playwright.config.ts.
 *
 * The TTA_ prefix is load-bearing: Windows defines USERNAME as a system
 * environment variable, and dotenv will not overwrite a variable that is
 * already set. A bare USERNAME key is silently ignored and the OS value wins,
 * which surfaces as an auth failure against a username nobody configured.
 */
export const CREDENTIALS = {
  username: process.env.TTA_USERNAME ?? '',
  password: process.env.TTA_PASSWORD ?? '',
} as const;

/**
 * Other accepted usernames. All six share the standard password; their verified
 * behavioural differences are in plan §5. Only the locked-out user earns a
 * scenario of its own — performance_glitch_user merely delays login by four
 * seconds and visual_user is functionally identical to the standard user.
 */
export const USERS = {
  lockedOut: 'locked_out_user',
  unknown: 'nonexistent_user',
  /** The standard username in the wrong case — matching is case-sensitive. */
  wrongCase: 'Standard_User',
} as const;

/**
 * The first card under the default Name (A to Z) sort. It is NOT one of the
 * five `TTA …` products: the locale comparison puts `Te` before `TT`, so the
 * red T-shirt sorts first (plan §1.3).
 */
export const FIRST_ITEM = {
  id: 'test-allthethings-tshirt-red',
  name: 'Test.allTheThings() T-Shirt (Red)',
  price: '$15.99',
} as const;

/** The whole catalogue is six cards. */
export const INVENTORY_COUNT = 6;

/** Overview totals for a single red T-shirt: 8% tax on $15.99 (plan §1.3). */
export const ORDER_TOTALS = {
  subtotal: 'Item total: $15.99',
  tax: 'Tax: $1.28',
  total: 'Total: $17.27',
} as const;

/** Overview totals when the cart is empty — see the pinned bug in plan §6.1. */
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

/** Valid checkout details used by every scenario that needs to get past step one. */
export const CUSTOMER = {
  firstName: 'John',
  lastName: 'Doe',
  postalCode: '12345',
} as const;

/**
 * Three spaces. Whitespace satisfies the HTML `required` attribute, so it slips
 * past native browser validation and reaches the application's own validator —
 * which is the only route to the app's "is required" banners (plan §3.6, §4.4).
 */
export const WHITESPACE = '   ';

/**
 * A postal code with no numeric content. Accepted by the application; pinned by
 * a test rather than endorsed (plan §6.2).
 */
export const NON_NUMERIC_POSTAL_CODE = 'not-a-zip!!';

/** The localStorage keys TTACart writes (plan §6.3, addendum §8.5 – §8.6). */
export const STORAGE_KEYS = {
  user: 'tta-cart-user',
  items: 'tta-cart-items',
  sort: 'tta-cart-sort',
  checkoutInfo: 'tta-cart-checkout-info',
} as const;

/** The first card under Name (Z to A) (plan addendum §8.4). */
export const LAST_ITEM_ALPHABETICALLY = 'TTA Practice Backpack';
