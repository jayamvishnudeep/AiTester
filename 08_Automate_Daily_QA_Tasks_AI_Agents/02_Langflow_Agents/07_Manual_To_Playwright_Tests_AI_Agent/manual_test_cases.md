# Manual test cases — Shopfront web store

Written the way a manual tester actually writes them: a title, what has to be
true before you start, numbered steps, and the result you expect at the end.
Nothing here mentions a selector or a framework. That is the point — turning
this into runnable code is the job the agent does.

Base URL: `https://shopfront.example.com`

---

## Feature: Login

### TC-01 — Sign in with valid credentials

**Precondition:** A registered account exists with email `ada@example.com` and
password `Correct-Horse-9`.

1. Open the login page.
2. Enter `ada@example.com` in the Email field.
3. Enter `Correct-Horse-9` in the Password field.
4. Click the **Sign in** button.

**Expected:** The shopper lands on the account dashboard, and the account menu
shows the name "Ada".

---

### TC-02 — Reject a wrong password

**Precondition:** The account `ada@example.com` exists.

1. Open the login page.
2. Enter `ada@example.com` in the Email field.
3. Enter `not-the-password` in the Password field.
4. Click the **Sign in** button.

**Expected:** An error message reads "Email or password is incorrect." The
shopper stays on the login page and the Password field is cleared.

---

### TC-03 — Require both fields before submitting

**Precondition:** None.

1. Open the login page.
2. Leave the Email and Password fields empty.

**Expected:** The **Sign in** button is disabled.

---

## Feature: Cart

### TC-04 — Add a single item to the cart

**Precondition:** The product "Linen Apron" is in stock.

1. Open the product page for "Linen Apron".
2. Click **Add to cart**.
3. Open the cart.

**Expected:** The cart holds one line for "Linen Apron" with quantity 1, and the
cart badge in the header reads 1.

---

### TC-05 — Change the quantity from the cart

**Precondition:** The cart already holds one "Linen Apron".

1. Open the cart.
2. Click the **+** stepper next to the "Linen Apron" line twice.

**Expected:** The quantity reads 3, the line total is three times the unit price,
and the cart badge reads 3.

---

### TC-06 — Remove the last item and see the empty state

**Precondition:** The cart holds exactly one line.

1. Open the cart.
2. Click **Remove** on the only line.

**Expected:** The cart shows the message "Your cart is empty", the cart badge
disappears, and the **Checkout** button is no longer shown.

---

## Feature: Checkout

### TC-07 — Pay with a saved card

**Precondition:** The shopper is signed in as `ada@example.com`, the cart holds
one "Linen Apron" at £24.00, and a card ending `4242` is saved on the account.

1. Open the cart and click **Checkout**.
2. Choose the saved card ending `4242`.
3. Click **Pay £24.00**.

**Expected:** A confirmation page appears with the heading "Order confirmed" and
an order number in the form `SF-` followed by six digits.

---

### TC-08 — Reject an expired card

**Precondition:** The shopper is at the payment step with a card expiring
`01/24` saved on the account.

1. Choose the card expiring `01/24`.
2. Click **Pay £24.00**.

**Expected:** An error reads "Card expired. Use a different card." The shopper
stays on the payment step and no order number is issued.

---

### TC-09 — Require a delivery address before paying

**Precondition:** The shopper is signed in with no saved address and the cart
holds one item.

1. Open the cart and click **Checkout**.

**Expected:** The **Pay** button is disabled and a prompt reads "Add a delivery
address to continue."

---

### TC-10 — Apply a promotion code

**Precondition:** The cart holds one "Linen Apron" at £24.00 and the code
`APRON10` gives 10% off.

1. Open the cart and click **Checkout**.
2. Enter `APRON10` in the Promotion code field.
3. Click **Apply**.

**Expected:** A discount line reads "-£2.40" and the total updates to £21.60.
