# Test Plan Addendum: TTACart — Paths the Primary Plan Does Not Reach

**Application under test:** https://app.thetestingacademy.com/playwright/ttacart/
**Extends:** `ttacart-e2e-order-plan.md` (§1 – §7). That document remains authoritative
for everything it covers; its §1 reference data applies here unchanged.
**Seed:** `src/seed.spec.ts`
**Verified:** 2026-09-26, Chromium, against the deployed application.

## Why this addendum exists

The primary plan automates 24 scenarios and all of them pass. Reviewing what it
*covers* rather than what it asserts turned up a set of controls that are checked
for existence but never exercised — the Remove button, Continue Shopping, Back
Home, the burger menu, the sort dropdown — and one whole class of route that is
never probed at all: reaching a checkout step by URL rather than by clicking
through to it.

Exercising those turned up **four suspected bugs that the primary plan does not
record**, one of which materially weakens four of its existing negatives. Each
value below was observed live; none is inferred.

---

## 8. Scenarios

### 8.1 Removing the only item empties the cart

1. Log in, add the first item, open the cart.
2. Click `[data-test="remove-test-allthethings-tshirt-red"]`.

**Expected:** stays on `.../cart`; `[data-test="cart-empty"]` reads
`Your cart is empty.`; no `[data-test="inventory-item"]` rows; the cart badge is
**removed from the DOM**; `tta-cart-items` becomes `[]`.

**Also observed:** the **Checkout link is still visible** on the emptied cart.
That is the same defect as §6.1, reached by removal rather than by never adding.

### 8.2 Continue Shopping returns to the products page with the cart intact

1. Log in, add the first item, open the cart.
2. Click `[data-test="continue-shopping"]`.

**Expected:** `.../inventory`, six cards, and the badge still reads `1` —
navigating away does not discard the cart.

### 8.3 Back Home from the confirmation page

1. Complete an order.
2. Click `[data-test="back-to-products"]`.

**Expected:** `.../inventory`; the cart is empty and the badge absent.

**Also observed:** `tta-cart-checkout-info` is **still present** afterwards, at
`{"firstName":"John","lastName":"Doe","postal":"12345"}`. This is direct
evidence for the hazard in primary-plan §6.3 — the key outlives the order.

### 8.4 Sorting Z to A changes the first product

1. Log in.
2. Select `za` in `#product-sort-container`.

**Expected:** the first `[data-test="inventory-item-name"]` becomes
`TTA Practice Backpack`. The four options are `az` / `za` / `lohi` / `hilo`
reading Name (A to Z) / Name (Z to A) / Price (low to high) / Price (high to low).

### 8.5 Logout ends the session, and the route guard holds

1. Log in, add the first item.
2. Open the burger menu, click `[data-test="logout-sidebar-link"]`.

**Expected:** back at the login URL with `TTACart - Login`; `tta-cart-user` is
gone; deep-linking `.../inventory` still redirects to the login page.

**Suspected bug, see §9.3:** `tta-cart-items` is **not** cleared by logout.

### 8.6 Reset App State clears the cart and the saved details but keeps the session

1. Reach the overview with an item and saved checkout details.
2. Open the burger menu, click `[data-test="reset-sidebar-link"]`.

**Expected:** `tta-cart-items` and `tta-cart-checkout-info` are both gone while
`tta-cart-user` remains, and the current page re-renders to zero line items and
`Total: $0.00`. This confirms the behaviour primary-plan §6.3 describes.

### 8.7 Browser Back after Finish allows the order to be placed again

*Pins suspected bug §9.1.*

1. Complete an order and land on `.../checkout-complete`.
2. Press the browser Back button.
3. Click `[data-test="finish"]` a second time.

**Observed:** step 2 returns to `.../checkout-step-two` showing
`Checkout: Overview` with zero line items and `Total: $0.00`, and the **Finish
button is still live**. Step 3 produces a second full
`Thank you for your order!` confirmation.

### 8.8 Checkout step two is reachable by URL, bypassing step one

*Pins suspected bug §9.2.*

1. Log in, add the first item. Do **not** visit step one.
2. Navigate directly to `.../checkout-step-two`.

**Observed:** the overview renders with the line item present and the badge at
`1`. No redirect, no error banner. `tta-cart-checkout-info` is absent — the
customer details were never supplied and are not required.

### 8.9 Finish from a URL-reached empty overview completes an order

*Pins suspected bug §9.2.*

1. Log in and add nothing.
2. Navigate directly to `.../checkout-step-two`.
3. Click Finish.

**Observed:** the overview shows `$0.00` throughout, Finish is visible, and
clicking it reaches `.../checkout-complete` with the full confirmation — an order
placed without a cart, without customer details, and without ever loading the
form that validates them.

---

## 9. Suspected bugs found by this addendum

### 9.1 An order can be placed repeatedly from one cart via browser Back

Finishing an order empties the cart but leaves the overview in history with a
live Finish button. Back, Finish, Back, Finish places as many confirmed orders
as the tester has patience for. Nothing invalidates the completed checkout.

Severity: the highest of the four. Duplicate order submission is a
money-handling defect, and the trigger is the browser's own Back button rather
than anything unusual.

### 9.2 Checkout step one can be skipped entirely by URL

`.../checkout-step-two` renders for any signed-in user regardless of whether
step one was ever completed, and Finish works from there.

This is the finding that matters most for the existing suite. Primary-plan
§4.1 – §4.4 carefully establish that First Name, Last Name and Postal Code are
each required, and those four tests are correct — the form does validate. But
the validation is **only** in the form, and the form is optional. Four scenarios
guard a door standing next to an open wall. They are still worth having; they
are just not evidence that customer details cannot be skipped, and nothing in
the primary plan says so.

### 9.3 The cart survives logout and is inherited by the next login

Logout removes `tta-cart-user` but leaves `tta-cart-items` intact. Logging back
in restores the previous cart — verified: badge returns to `1` with the red
T-shirt still in it.

On a shared machine the next person to sign in inherits the previous person's
cart. Reset App State clears it (§8.6), but logout is the action a user would
reasonably expect to.

### 9.4 Checkout is still offered on an emptied cart

A cart emptied by Remove still shows the Checkout link, which leads to a
completable $0.00 order. Same defect as primary-plan §6.1 by a different route,
recorded here because a fix that special-cases "never added anything" would miss
this path.

---

## 10. Coverage added

| Section | Scenario | Type |
| --- | --- | --- |
| 8.1 | Removing the only item empties the cart | Negative / alternate path |
| 8.2 | Continue Shopping keeps the cart | Positive checkpoint |
| 8.3 | Back Home from confirmation | Positive checkpoint |
| 8.4 | Sorting Z to A | Positive checkpoint |
| 8.5 | Logout ends the session | Negative |
| 8.6 | Reset App State | Utility / state |
| 8.7 | Repeat order via browser Back | Negative (pins §9.1) |
| 8.8 | Step two reachable by URL | Negative (pins §9.2) |
| 8.9 | Finish from a URL-reached empty overview | Negative (pins §9.2) |

Every scenario is independent and may run in any order. The tests pinning §9.1 –
§9.4 assert **current** behaviour so that a fix fails loudly and is updated on
purpose; passing is not approval.
