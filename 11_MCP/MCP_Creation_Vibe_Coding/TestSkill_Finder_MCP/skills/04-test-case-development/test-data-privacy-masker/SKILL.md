---
name: test-data-privacy-masker
description: >-
  Plan safe test data: mask, subset or synthesise data so no real personal data reaches test
  environments. Use when a team says "can we copy production data to staging", "mask this
  database for testing", "we need realistic but safe test data", or must meet GDPR, HIPAA or
  PCI DSS in testing. Produces a data inventory with sensitivity levels, a masking rule per
  field (substitution, shuffling, tokenisation, synthetic generation), referential-integrity
  rules, and checks that prove the masked data is safe and still useful.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Case Development
  version: 1.0.0
---

# Test Data Privacy Masker

You give testers **realistic data that cannot hurt a real person** — production-like shape,
no production identities.

## When to use
- Someone wants production data in a test environment.
- Test data must satisfy privacy rules (GDPR, HIPAA, PCI DSS) or company policy.

## Workflow
1. **Inventory the data** — tables and fields, and classify each: direct identifier (name,
   email, phone, national ID), quasi-identifier (birth date, postcode), sensitive (health,
   payment, salary), non-sensitive.
2. **Choose a technique per field:**
   - Substitution with realistic fake values (names, emails on a reserved domain such as
     example.com or example.test).
   - Format-preserving tokenisation for IDs that must keep their format.
   - Shuffling within a column for distributions that must stay realistic.
   - Generalisation (birth date → year) for quasi-identifiers.
   - Never copy card numbers or secrets: use the payment provider's test card numbers.
3. **Keep integrity** — the same real value maps to the same masked value across tables so
   joins still work; keep foreign keys consistent.
4. **Subset** — take only the slice tests need, which shrinks both risk and cost.
5. **Verify** — scan the masked data for leftover real patterns (real email domains, valid
   national ID checksums), and run a smoke test to show the data still works.

## Output shape
```
## Test Data Plan — <system>
| Table.field | Class | Technique | Rule |
|-------------|-------|-----------|------|
| users.email | direct identifier | substitution | user{id}@example.test |
| users.birth_date | quasi-identifier | generalisation | keep year, set 01-01 |
| payments.card_number | sensitive | replace | provider test card numbers only |
Integrity: users.id → orders.user_id kept consistent
Verification: leak scan + checkout smoke test on masked data
--- HUMAN REVIEW GATE --- "Privacy or data-protection owner approves before any data moves"
```

## Guardrails
- Never move unmasked production personal data into a test environment.
- Masking must be irreversible for anyone with access to the test environment.
- The data-protection owner signs off on the plan; the skill does not.
