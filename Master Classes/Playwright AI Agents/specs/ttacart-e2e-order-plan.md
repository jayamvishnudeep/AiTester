# Test Plan: TTACart — End-to-End Order Placement

**Application under test:** https://app.thetestingacademy.com/playwright/ttacart/
**Seed:** `src/seed.spec.ts`
**Assumptions:** Every scenario starts from a fresh, logged-out browser context — no `localStorage`
state, no cart contents, no saved checkout details. See §6 for why a genuinely clean context matters
in this application.

**Credentials:** username `standard_user`, password `tta_secret`, supplied through the environment
variables `TTA_USERNAME` and `TTA_PASSWORD`. The names are deliberately prefixed: Windows defines
`USERNAME` as a system environment variable, and `dotenv` will not overwrite an already-set variable,
so a bare `USERNAME` key in `.env` is silently ignored and the OS value wins.

**Accepted usernames** (all share password `tta_secret`): `standard_user`, `locked_out_user`,
`problem_user`, `performance_glitch_user`, `error_user`, `visual_user`. Their verified behavioural
differences are recorded in §5 — only `standard_user` is suitable for the end-to-end scenario.

**The scenario under test:** log in → add the first item to the cart → Checkout → enter customer
details → Continue → Finish → verify the "Thank you for your order!" confirmation.

All expected values below were observed live in Chromium against the deployed application. Points
where TTACart diverges from the saucedemo.com application it is modelled on are called out inline;
behaviour that looks like a genuine defect is recorded in §6 as a suspected bug rather than being
quietly baked into an assertion.

---

## 1. Reference data — confirmed selectors and values

### 1.1 Page routes and titles

| Page | URL (as the browser reports it) | `document.title` | `[data-test="title"]` |
| --- | --- | --- | --- |
| Login | `https://app.thetestingacademy.com/playwright/ttacart/` | `TTACart - Login` | — |
| Products | `.../ttacart/inventory` | `TTACart - Products` | `Products` |
| Cart | `.../ttacart/cart` | `TTACart - Your Cart` | `Your Cart` |
| Checkout step one | `.../ttacart/checkout-step-one` | `TTACart - Checkout: Your Information` | `Checkout: Your Information` |
| Checkout step two | `.../ttacart/checkout-step-two` | `TTACart - Checkout: Overview` | `Checkout: Overview` |
| Confirmation | `.../ttacart/checkout-complete` | `TTACart - Checkout: Complete!` | `Checkout: Complete!` |

The in-page links target `./inventory.html`, `./cart.html` and so on, but the server serves them
without the extension: requesting `inventory.html` settles on `.../ttacart/inventory`. Assert on the
extension-less form.

### 1.2 Selectors

**Login page**

| Element | Selector | Notes |
| --- | --- | --- |
| Username field | `#user-name` / `[data-test="username"]` | `name="user-name"`, `required` |
| Password field | `#password` / `[data-test="password"]` | `type="password"`, `required` |
| Login button | `#login-button` / `[data-test="login-button"]` | `type="submit"` inside `#login-form` |
| Error banner | `#login-error` / `[data-test="error"]` | `role="alert"`; gains class `is-visible` when populated |
| Login card | `[data-test="login-container"]` | |

**Shell (all signed-in pages)**

| Element | Selector |
| --- | --- |
| Header | `[data-test="primary-header"]` |
| Burger menu button | `#react-burger-menu-btn` / `[data-test="open-menu"]` |
| Cart link | `#shopping_cart_container` / `[data-test="shopping-cart-link"]` |
| Cart badge | `[data-test="shopping-cart-badge"]` — **absent from the DOM when the cart is empty**, not merely hidden |
| Page heading | `[data-test="title"]` |
| Logout / Reset App State | `#logout_sidebar_link`-equivalent links inside `[data-test="side-menu"]` (`[data-action="logout"]`, `[data-action="reset"]`) |

**Products page**

| Element | Selector |
| --- | --- |
| Item card | `.inventory-item` / `[data-test="inventory-item"]` (6 cards) |
| Item name | `[data-test="inventory-item-name"]` |
| Item price | `[data-test="inventory-item-price"]` |
| Add/remove button | `.item-btn` within the card |
| First item's add button | `[data-test="add-to-cart-test-allthethings-tshirt-red"]` |
| Same button after adding | `[data-test="remove-test-allthethings-tshirt-red"]`, class `item-btn is-remove` |
| Sort dropdown | `#product-sort-container` / `[data-test="product-sort-container"]` |

**Cart page**

| Element | Selector |
| --- | --- |
| Line item row | `[data-test="inventory-item"]` (class `.cart-row`) |
| Quantity | `[data-test="item-quantity"]` |
| Remove button | `.btn-remove` / `[data-test="remove-<product-id>"]` |
| Continue Shopping | `[data-test="continue-shopping"]` |
| Checkout | `[data-test="checkout"]` — an `<a href="./checkout-step-one.html">`, not a button |
| Empty-cart message | `[data-test="cart-empty"]` → `Your cart is empty.` |

**Checkout step one**

| Element | Selector |
| --- | --- |
| Form | `#checkout-form` — carries `novalidate`; the three inputs have **no** `required` attribute |
| First Name | `#first-name` / `[data-test="firstName"]` |
| Last Name | `#last-name` / `[data-test="lastName"]` |
| Zip/Postal Code | `#postal-code` / `[data-test="postalCode"]` |
| Error banner | `#checkout-error` / `[data-test="error"]` |
| Cancel | `[data-test="cancel"]` — an `<a href="./cart.html">` |
| Continue | `#continue-btn` / `[data-test="continue"]` — `type="submit" form="checkout-form"` |

**Checkout step two (overview)**

| Element | Selector |
| --- | --- |
| Line item row | `[data-test="inventory-item"]` |
| Payment information | `[data-test="payment-info-value"]` |
| Shipping information | `[data-test="shipping-info-value"]` |
| Item total | `[data-test="subtotal-label"]` |
| Tax | `[data-test="tax-label"]` |
| Total | `[data-test="total-label"]` |
| Cancel | `[data-test="cancel"]` — an `<a href="./cart.html">` |
| Finish | `#finish-btn` / `[data-test="finish"]` |

**Confirmation page**

| Element | Selector |
| --- | --- |
| Container | `[data-test="checkout-complete-container"]` |
| Thank-you heading | `[data-test="complete-header"]` → `Thank you for your order!` |
| Body copy | `[data-test="complete-text"]` → `Your order has been dispatched, and will arrive just as fast as the TTA Express pony can get there!` |
| Tick graphic | `[data-test="pony-express"]` |
| Back Home | `[data-test="back-to-products"]` → label `Back Home` |

### 1.3 The first item, and the money

With the default sort **Name (A to Z)**, the first card on the products page is
**`Test.allTheThings() T-Shirt (Red)`** at **`$15.99`** (product id `test-allthethings-tshirt-red`).
It sorts ahead of the five `TTA …` products because the locale comparison puts `Te` before `TT`.

For that single item the overview page shows, verified live:

- `Item total: $15.99`
- `Tax: $1.28` (8%, rounded to the cent)
- `Total: $17.27`
- `Payment Information:` → `TTACard #31337`
- `Shipping Information:` → `Free TTA Express Delivery!`

> **Note (divergence from saucedemo.com):** the products, ids, prices, card name and courier string
> are TTACart's own. The first alphabetical item there is `Sauce Labs Backpack`; here it is the red
> T-shirt. Any assertion copied from a saucedemo suite will fail.

### 1.4 Exact error strings

| Condition | Banner text (verbatim) |
| --- | --- |
| Wrong password / unknown user / wrong-case username / whitespace-only password | `Epic sadface: Username and password do not match any user in this service` |
| Locked-out user | `Epic sadface: Sorry, this user has been locked out.` |
| Whitespace-only username | `Epic sadface: Username is required` |
| First Name blank or whitespace-only | `Error: First Name is required` |
| Last Name blank or whitespace-only | `Error: Last Name is required` |
| Postal Code blank or whitespace-only | `Error: Postal Code is required` |

The login banner and the checkout banner both live at `[data-test="error"]` on their respective
pages and both gain the class `is-visible` when populated; when there is no error the element is
present but empty, so assert on text rather than on presence.

---

## 2. Positive cases

### 2.1 Full happy path: login → add first item → checkout → confirmation (primary scenario)

**Steps:**

1. Navigate to `https://app.thetestingacademy.com/playwright/ttacart/`.
2. Enter username `standard_user` into `#user-name`.
3. Enter password `tta_secret` into `#password`.
4. Click **Login** (`#login-button`).
5. On the products page, click the **Add to cart** button of the first `.inventory-item` card
   (`[data-test="add-to-cart-test-allthethings-tshirt-red"]`).
6. Click the cart link in the header (`[data-test="shopping-cart-link"]`).
7. Click **Checkout** (`[data-test="checkout"]`).
8. Enter First Name `John`, Last Name `Doe`, Zip/Postal Code `12345`.
9. Click **Continue** (`[data-test="continue"]`).
10. Click **Finish** (`[data-test="finish"]`).

**Expected outcome:** the flow completes without a single error banner and ends on
`.../ttacart/checkout-complete`, where `[data-test="complete-header"]` reads
**`Thank you for your order!`** and `[data-test="complete-text"]` reads `Your order has been
dispatched, and will arrive just as fast as the TTA Express pony can get there!`. A **Back Home**
link is offered. The cart badge is gone from the header, because finishing the order empties the
cart.

**Failure conditions:** any error banner becoming visible; any URL other than the one expected at
each hop; the thank-you heading absent or worded differently.

### 2.2 Successful login lands on the products page

**Steps:**

1. Navigate to the login page.
2. Enter `standard_user` / `tta_secret` and click **Login**.

**Expected outcome:** the browser settles on `.../ttacart/inventory` with `document.title` equal to
`TTACart - Products` and `[data-test="title"]` reading `Products`. Exactly six `.inventory-item`
cards are rendered; the sort dropdown shows **Name (A to Z)** selected; the header exposes the
burger menu and the cart link, and **no** cart badge, because the cart is empty. The first card is
`Test.allTheThings() T-Shirt (Red)` at `$15.99`. Navigation is immediate — no interstitial.

### 2.3 Cart badge updates when the first item is added

**Steps:**

1. Log in as `standard_user`.
2. Click **Add to cart** on the first inventory card.

**Expected outcome:** `[data-test="shopping-cart-badge"]` is inserted into the header and reads
`1`. The clicked button re-renders as **Remove** with class `item-btn is-remove` and
`data-test="remove-test-allthethings-tshirt-red"`. No page navigation occurs; the URL stays
`.../ttacart/inventory`.

> **Note:** an earlier TTACart plan in this repository stated that the button "remains 'Add to
> cart'-labelled and the cart badge is the source of truth". That is incorrect — re-verified in the
> browser, the label and the `data-test` attribute both flip. Assert on either.

### 2.4 Cart page shows the correct line item

**Steps:**

1. Log in as `standard_user` and add the first item.
2. Click the cart link in the header.

**Expected outcome:** the browser is on `.../ttacart/cart`, `[data-test="title"]` reads
`Your Cart`, and exactly one `[data-test="inventory-item"]` row is present:
name `Test.allTheThings() T-Shirt (Red)`, price `$15.99`, quantity `1`. The header badge still
reads `1`. **Remove**, **Continue Shopping** and **Checkout** are all available; Continue Shopping
points at `./inventory.html` and Checkout at `./checkout-step-one.html`.

### 2.5 Checkout information form accepts valid details and advances

**Steps:**

1. Reach `.../ttacart/checkout-step-one` with one item in the cart.
2. Confirm the three fields start empty (true only from a clean context — see §6.3).
3. Enter First Name `John`, Last Name `Doe`, Zip/Postal Code `12345`.
4. Click **Continue**.

**Expected outcome:** no error banner appears and the browser advances to
`.../ttacart/checkout-step-two` with `[data-test="title"]` reading `Checkout: Overview`.

### 2.6 Overview page shows a correct order summary

**Precondition:** 2.5 completed with the single red T-shirt in the cart.

**Expected outcome:** the overview lists one `[data-test="inventory-item"]` row —
`Test.allTheThings() T-Shirt (Red)`, `$15.99`, quantity `1` — followed by
`[data-test="payment-info-value"]` = `TTACard #31337`,
`[data-test="shipping-info-value"]` = `Free TTA Express Delivery!`, and a Price Total block reading
`Item total: $15.99`, `Tax: $1.28`, `Total: $17.27`. **Cancel** and **Finish** are both present, and
the header badge still reads `1`.

Assert the money as displayed strings including the labels; the tax is 8% of the item total rounded
to the cent, so `$15.99 → $1.28 → $17.27` arithmetically checks out.

> **Note:** the overview does not echo the customer name or postal code entered at step one, so
> there is nothing to assert about the details themselves on this page.

### 2.7 Finish reaches the confirmation page

**Precondition:** on `.../ttacart/checkout-step-two` with one item.

**Steps:**

1. Click **Finish** (`[data-test="finish"]`).

**Expected outcome:** the browser navigates to `.../ttacart/checkout-complete`, `document.title` is
`TTACart - Checkout: Complete!`, `[data-test="title"]` reads `Checkout: Complete!`, and
`[data-test="complete-header"]` reads exactly **`Thank you for your order!`**. The body copy, the
tick graphic (`[data-test="pony-express"]`) and the **Back Home** link are present. The cart is
emptied as part of finishing, so the header badge is no longer in the DOM.

---

## 3. Negative cases — login

### 3.1 Invalid password

**Steps:**

1. Navigate to the login page.
2. Enter username `standard_user`.
3. Enter password `wrong_password`.
4. Click **Login**.

**Expected outcome:** the user stays on `.../ttacart/` and `[data-test="error"]` reads
`Epic sadface: Username and password do not match any user in this service`. No session is created.

### 3.2 Locked-out user

**Steps:**

1. Navigate to the login page.
2. Enter username `locked_out_user` and password `tta_secret`.
3. Click **Login**.

**Expected outcome:** the user stays on the login page and the banner reads
`Epic sadface: Sorry, this user has been locked out.` Verified that no session is written — the
`tta-cart-user` key in `localStorage` remains `null`, so the products page cannot be reached by
deep link afterwards.

### 3.3 Unknown username

**Steps:**

1. Navigate to the login page.
2. Enter username `nonexistent_user` and password `tta_secret`.
3. Click **Login**.

**Expected outcome:** the banner reads
`Epic sadface: Username and password do not match any user in this service` — identical to 3.1. The
app does not distinguish an unknown user from a bad password, so this test must not assert a
distinct message.

### 3.4 Empty username

**Steps:**

1. Navigate to the login page.
2. Leave the username blank.
3. Enter password `tta_secret`.
4. Click **Login**.

**Expected outcome:** submission is blocked by **native browser validation**, not by the
application. `#user-name` reports `validity.valueMissing === true` (Chromium's message is
`Please fill in this field.`), `[data-test="error"]` stays **empty**, and the URL does not change.

> **Note (divergence from saucedemo.com):** saucedemo shows `Epic sadface: Username is required` in
> its error banner here. TTACart's inputs carry the HTML `required` attribute, so the browser
> intercepts the submit and the application's own "Username is required" branch is never reached.
> Automation should assert `validity.valueMissing` on the field rather than any message text, since
> the tooltip wording is browser-specific. **Do not** assert the `Epic sadface: Username is
> required` string for this case — see 3.6 for the only way to surface it.

### 3.5 Empty password

**Steps:**

1. Navigate to the login page.
2. Enter username `standard_user`.
3. Leave the password blank.
4. Click **Login**.

**Expected outcome:** as in 3.4 — `#password` reports `validity.valueMissing === true` with the
Chromium message `Please fill in this field.`, the error banner stays empty and the page does not
navigate. The application's `Epic sadface: Password is required` branch is unreachable.

### 3.6 Whitespace-only username

**Steps:**

1. Navigate to the login page.
2. Enter three space characters into `#user-name`.
3. Enter password `tta_secret`.
4. Click **Login**.

**Expected outcome:** native validation is satisfied (the field is not empty), so the application's
own validator runs and trims the value. `[data-test="error"]` becomes visible reading
`Epic sadface: Username is required`. This is the only observed route to that string.

### 3.7 Whitespace-only password

**Steps:**

1. Navigate to the login page.
2. Enter username `standard_user`.
3. Enter three space characters into `#password`.
4. Click **Login**.

**Expected outcome:** the banner reads
`Epic sadface: Username and password do not match any user in this service` — **not** a
"required" message. Unlike the username, the password is not trimmed before the comparison, so
whitespace is treated as a genuine (wrong) password. Confirmed in the browser.

### 3.8 Username matching is case-sensitive

**Steps:**

1. Navigate to the login page.
2. Enter username `Standard_User` and password `tta_secret`.
3. Click **Login**.

**Expected outcome:** login is refused with
`Epic sadface: Username and password do not match any user in this service`. Usernames are matched
exactly; no normalisation is applied.

### 3.9 Checkout pages are not reachable while logged out

**Steps:**

1. Clear all site storage so no session exists.
2. Request `https://app.thetestingacademy.com/playwright/ttacart/checkout-step-one.html` directly.

**Expected outcome:** the application redirects to the login page — the browser settles on
`https://app.thetestingacademy.com/playwright/ttacart/` with title `TTACart - Login`. The same guard
protects `inventory`, `cart`, `checkout-step-two` and `checkout-complete`, so no step of the order
flow can be entered by deep link without signing in.

---

## 4. Negative cases — cart and checkout

**Precondition for 4.1 – 4.6:** logged in as `standard_user` with the first item in the cart, on
`.../ttacart/checkout-step-one` unless stated otherwise.

### 4.1 First Name left blank

**Steps:**

1. Leave **First Name** blank.
2. Enter Last Name `Doe` and Zip/Postal Code `12345`.
3. Click **Continue**.

**Expected outcome:** the user stays on `.../ttacart/checkout-step-one`; `[data-test="error"]`
becomes visible reading `Error: First Name is required`. The field values already entered are
retained, and the overview page is never reached.

### 4.2 Last Name left blank

**Steps:**

1. Enter First Name `John`, leave **Last Name** blank, enter Zip/Postal Code `12345`.
2. Click **Continue**.

**Expected outcome:** stays on step one with the banner reading `Error: Last Name is required`.

### 4.3 Zip/Postal Code left blank

**Steps:**

1. Enter First Name `John` and Last Name `Doe`, leave **Zip/Postal Code** blank.
2. Click **Continue**.

**Expected outcome:** stays on step one with the banner reading `Error: Postal Code is required`.

> **Validation order:** the three checks run first-name → last-name → postal-code and stop at the
> first failure, so only one message is ever shown at a time. A test that blanks two fields will see
> only the earlier field's message. This is why 4.1 – 4.3 each blank exactly one field.

### 4.4 Whitespace-only field values are treated as blank

**Steps:**

1. Enter three space characters into **First Name**.
2. Enter Last Name `Doe` and Zip/Postal Code `12345`.
3. Click **Continue**.

**Expected outcome:** the banner reads `Error: First Name is required` and the user stays on step
one. The submitted value is trimmed before validation; the field itself is **not** cleared — it
still visibly contains the spaces. The same holds for whitespace-only Last Name and Postal Code,
producing their respective messages.

### 4.5 Cancel on the checkout information step

**Steps:**

1. On `.../ttacart/checkout-step-one`, click **Cancel** (`[data-test="cancel"]`).

**Expected outcome:** the browser returns to `.../ttacart/cart`. The cart still holds its single
`Test.allTheThings() T-Shirt (Red)` row and the header badge still reads `1` — nothing is discarded.

### 4.6 Cancel on the overview step

**Steps:**

1. Complete step one with valid details to reach `.../ttacart/checkout-step-two`.
2. Click **Cancel** (`[data-test="cancel"]`).

**Expected outcome:** the browser returns to **`.../ttacart/cart`** with one line item and the badge
reading `1`. The order is not placed.

> **Note (divergence from saucedemo.com):** on saucedemo, Cancel on the overview step returns the
> user to the **products** page; TTACart's overview Cancel is an `<a href="./cart.html">` and goes to
> the **cart**. Confirmed by execution. Both of TTACart's Cancel controls lead to the cart.

### 4.7 A non-numeric postal code is accepted

**Steps:**

1. Enter First Name `John`, Last Name `Doe`.
2. Enter `not-a-zip!!` into **Zip/Postal Code**.
3. Click **Continue**.

**Expected outcome:** **no error is raised** — the application advances to
`.../ttacart/checkout-step-two` and the order can be finished normally. The only rule applied to
the postal code is "non-empty after trimming"; there is no length, numeric or format check. This
scenario is included to pin the current behaviour, so a future tightening of validation is caught as
a deliberate change rather than a regression. See §6.2.

### 4.8 Checking out with an empty cart

**Steps:**

1. Log in as `standard_user` and do not add anything, or remove the only item from the cart.
2. On `.../ttacart/cart`, confirm `[data-test="cart-empty"]` reads `Your cart is empty.`
3. Click **Checkout**.
4. Enter First Name `John`, Last Name `Doe`, Zip/Postal Code `12345` and click **Continue**.
5. Click **Finish**.

**Expected outcome (current behaviour, observed):** every step is allowed. Checkout step one opens
even with nothing in the cart; the overview renders **no** `[data-test="inventory-item"]` rows and
shows `Item total: $0.00`, `Tax: $0.00`, `Total: $0.00`; Finish reaches
`.../ttacart/checkout-complete` and displays `Thank you for your order!` for an order containing
nothing.

This is recorded as a **suspected bug** (§6.1). Write the test to assert the observed behaviour and
label it explicitly as pinning a defect, so that when the application starts blocking empty-cart
checkout the test fails loudly and is updated on purpose.

---

## 5. Behaviour of the other accepted usernames (verified)

Each of the six documented usernames was exercised in the browser. Only `standard_user` and
`visual_user` are safe for deterministic end-to-end automation.

| Username | Verified behaviour |
| --- | --- |
| `standard_user` | Baseline. Logs in immediately; `document.body.className` is empty; full flow deterministic. |
| `locked_out_user` | Cannot log in at all — see 3.2. No session is created. |
| `problem_user` | Logs in (`body.problem-user`). **The sort selection is ignored**, so the products render in raw source order and the first card becomes `TTA Practice Backpack` at `$29.99`, not the red T-shirt — any test that adds "the first item" gets a different product and different totals. Product images are deliberately swapped to the wrong pictures. And the **first** fully valid submit of checkout step one is rejected: the First Name field is wiped and `Error: First Name is required` is shown; submitting again succeeds. |
| `performance_glitch_user` | Logs in successfully but slowly: on submit the Login button is disabled and its label changes to `Logging in...`, the page stays on the login URL for roughly four seconds, then lands on `.../ttacart/inventory`. Everything after login is identical to `standard_user`. |
| `error_user` | Logs in (`body.error-user`), but **add-to-cart is intermittently a silent no-op** — measured 13 misses in 40 clicks (~30%), with no error shown and the badge simply not changing. Unsuitable for automation; any add-to-cart assertion is flaky by design. |
| `visual_user` | Logs in (`body.visual-user`). **Functionally identical** to `standard_user`: same A-to-Z ordering, same first item, same flow, same totals. The only observed difference is cosmetic — the header cart link is nudged 8px right (`transform: matrix(1, 0, 0, 1, 8, 0)` versus `none`). Not usable as a functional-failure case; it is a visual-regression fixture. |

**Recommended coverage:** use `standard_user` for §2, `locked_out_user` for 3.2, and treat the
`problem_user` / `performance_glitch_user` / `error_user` quirks as their own suite rather than
mixing them into the end-to-end scenario.

---

## 6. Suspected bugs and application-specific hazards

### 6.1 Suspected bug — an empty cart can be checked out to a completed $0.00 order

Verified end to end: with `[data-test="cart-empty"]` showing `Your cart is empty.`, clicking
**Checkout** still opens step one, valid details still advance to the overview, the overview shows
`Item total: $0.00` / `Tax: $0.00` / `Total: $0.00` with no line items, and **Finish** produces the
full `Thank you for your order!` confirmation. A storefront should not be able to confirm an order
with nothing in it. Treat 4.8 as pinning current behaviour, not as approved behaviour.

### 6.2 Suspected bug / gap — no format validation on the postal code

`not-a-zip!!` is accepted and persisted, and the order completes (4.7). Only emptiness is checked.
Whether this matters is a product decision, but it is worth raising: there is no length, character
or numeric constraint of any kind on the field.

### 6.3 Hazard — checkout details persist in `localStorage` and pre-fill the form

On a successful **Continue**, the entered details are written to `localStorage` under
`tta-cart-checkout-info`, and step one **pre-fills** from that key on every subsequent visit. The key
is **not** cleared when the order is finished: after a completed order the stored value was still
`{"firstName":"John","lastName":"Doe","postal":"12345"}`.

Consequences for testing:

- The "form starts empty" expectation in 2.5 holds only from a genuinely clean context.
- The blank-field negatives (4.1 – 4.4) will **silently pass validation** if a previous test left
  values behind, because the field is pre-filled rather than blank — the case under test evaporates.
- Therefore every scenario must begin by clearing site storage (or use a fresh browser context), and
  tests must not depend on execution order. The relevant keys are `tta-cart-user`,
  `tta-cart-items`, `tta-cart-sort` and `tta-cart-checkout-info`; the sidebar **Reset App State**
  action clears the last three but leaves the session intact.

This differs from saucedemo.com, where the checkout form is always presented empty.

### 6.4 Hazard — the cart badge is absent, not hidden

When the cart is empty, `[data-test="shopping-cart-badge"]` is removed from the DOM entirely.
Assert non-existence for the empty state and a text value of `1` for the populated state; an
assertion written as "badge text is empty" will fail.

### 6.5 Hazard — Checkout, Cancel and Continue Shopping are links, not buttons

`[data-test="checkout"]`, both `[data-test="cancel"]` controls and
`[data-test="continue-shopping"]` are anchors; only **Login**, **Continue** and **Finish** are real
buttons. Locators built on `getByRole('button')` will miss the anchors — use the `data-test`
attributes, which are stable across all six pages.

---

## 7. Coverage summary

| Section | Scenario | Type |
| --- | --- | --- |
| 2.1 | Full happy path: login → add first item → checkout → confirmation | Positive (primary) |
| 2.2 | Successful login lands on the products page | Positive checkpoint |
| 2.3 | Cart badge updates when the first item is added | Positive checkpoint |
| 2.4 | Cart page shows the correct line item | Positive checkpoint |
| 2.5 | Checkout information form accepts valid details and advances | Positive checkpoint |
| 2.6 | Overview page shows a correct order summary | Positive checkpoint |
| 2.7 | Finish reaches the confirmation page | Positive checkpoint |
| 3.1 | Invalid password | Negative |
| 3.2 | Locked-out user | Negative |
| 3.3 | Unknown username | Negative |
| 3.4 | Empty username | Negative |
| 3.5 | Empty password | Negative |
| 3.6 | Whitespace-only username | Negative |
| 3.7 | Whitespace-only password | Negative |
| 3.8 | Username matching is case-sensitive | Negative |
| 3.9 | Checkout pages unreachable while logged out | Negative |
| 4.1 | First Name left blank | Negative |
| 4.2 | Last Name left blank | Negative |
| 4.3 | Zip/Postal Code left blank | Negative |
| 4.4 | Whitespace-only field values treated as blank | Negative |
| 4.5 | Cancel on the checkout information step | Negative / alternate path |
| 4.6 | Cancel on the overview step | Negative / alternate path |
| 4.7 | Non-numeric postal code is accepted | Negative (pins a gap) |
| 4.8 | Checking out with an empty cart | Negative (pins a suspected bug) |

All scenarios are independent and may be run in any order, provided each one starts by clearing site
storage as required by §6.3.
