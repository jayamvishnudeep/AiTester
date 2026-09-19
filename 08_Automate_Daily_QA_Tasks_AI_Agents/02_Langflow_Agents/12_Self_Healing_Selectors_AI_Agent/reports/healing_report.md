# Selector healing report

*Generated 2026-09-19 by the Self-Healing Selectors agent. Every selector proposed below was run against the current page and resolves to exactly one element.*

## At a glance

| | |
|---|---|
| Selectors checked | 6 |
| **Healed** | **4** |
| Need a decision | 0 |
| Element gone | 1 |
| Were never broken | 1 |
| Previous DOM supplied | yes |
| Elements searched | 48 |

## Healed (4)

| Was | Now | Via | Score |
|---|---|---|---:|
| `.btn-primary.checkout-submit` | `page.getByTestId('place-order')` | test id | 49 |
| `#summary > div:nth-child(4) > span.summary-row__value` | `page.getByTestId('order-total')` | test id | 91 |
| `.basket-item:nth-child(2) .basket-item__remove` | `page.getByRole('button', name='Remove USB-C cable')` | role and name | 82 |
| `.panel--payment .input--text` | `page.locator('#card-number')` | id | 94 |

Why each one matched:

- `.btn-primary.checkout-submit` — sits beside the same content; still a button; under the 'Checkout' heading
    - or `page.getByRole('button', name='Pay now')` (via role and name)
    - or `page.getByText('Pay now', exact=True)` (via text)
- `#summary > div:nth-child(4) > span.summary-row__value` — accessible name '£128.49'; text '£128.49'; sits beside the same content; inside the same identified region
    - or `page.getByText('£128.49', exact=True)` (via text)
- `.basket-item:nth-child(2) .basket-item__remove` — accessible name 'Remove USB-C cable'; text 'Remove'; sits beside the same content; still a button
- `.panel--payment .input--text` — same id 'card-number'; accessible name 'Card number'; same name attribute 'cardNumber'; sits beside the same content
    - or `page.getByRole('textbox', name='Card number')` (via role and name)
    - or `page.getByLabel('Card number')` (via label)

## Element gone (1)

Nothing in the current page corresponds to these. A test pointing at a removed feature needs rewriting, not a new selector.

- `//a[@class='link link--muted js-apply-gift']` — best match scored 20, below the threshold of 45

## Were never broken (1)

- `#ship-post` — still resolves to exactly one element

## Replacements

Ready to apply. The JSON beside this report carries the same pairs for a codemod.

```text
.btn-primary.checkout-submit
  -> page.getByTestId('place-order')
#summary > div:nth-child(4) > span.summary-row__value
  -> page.getByTestId('order-total')
.basket-item:nth-child(2) .basket-item__remove
  -> page.getByRole('button', name='Remove USB-C cable')
.panel--payment .input--text
  -> page.locator('#card-number')
```

---

## Review

*This section is written by a language model from the evidence above. That each selector resolves uniquely is checked in code; whether it is the element the test meant is the judgement below.*

Safe to apply
- `page.locator('#card-number')`: High confidence (94/100). The ID, accessible name, and name attribute all match the original, confirming it is the specific card number input field.
- `page.getByTestId('order-total')`: High confidence (91/100). Located in the same region with matching text and accessible name, clearly identifying the total price display.
- `page.getByRole('button', name='Remove USB-C cable')`: High confidence (82/100). The accessible name explicitly identifies the action and the specific item, making it a robust replacement for the positional selector.

Check before applying
- `page.getByTestId('place-order')`: The match score is low (49/100). While it is a button under the Checkout heading, the evidence is thin. Verify that this test ID is specifically attached to the final submission action and not a generic "Continue" or "Add to Cart" button that might have been moved or renamed. If the test ID is generic, prefer the alternative `page.getByRole('button', name='Pay now')` if the text is stable.

Needs a person
- `//a[@class='link link--muted js-apply-gift']`: This element is gone. The test likely needs rewriting rather than re-pointing, as the gift application feature may have been removed or significantly restructured in the UI.
