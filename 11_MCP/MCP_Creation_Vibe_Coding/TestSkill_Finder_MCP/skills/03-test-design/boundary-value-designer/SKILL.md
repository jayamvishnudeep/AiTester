---
name: boundary-value-designer
description: >-
  Design test inputs with boundary value analysis, equivalence partitioning and decision
  tables. Use when a tester says "what values should I test for this field", "do BVA for age
  18-60", "equivalence classes for this form", "decision table for these rules", or shares
  input constraints or business rules. Produces the partitions, the exact boundary values
  (min-1, min, min+1, max-1, max, max+1) and the rule combinations, each with its expected
  outcome traced to the rule.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Design
  version: 1.0.0
---

# Boundary Value Designer

You find the **few input values most likely to break the code** — partitions, their edges and
rule combinations — instead of testing values at random.

## When to use
- A field, parameter or API property has a range, length, format or set of allowed values.
- Business rules combine several conditions (discounts, eligibility, pricing).

## Workflow
1. **Write down the rule exactly** — type, range, length, format, required or optional, and
   whether each limit is inclusive. If the spec does not say whether 60 is allowed, ask.
2. **Equivalence partitions** — valid classes and invalid classes (below range, above range,
   wrong type, empty, null, wrong format). One representative value per class.
3. **Boundary values** — for each limit: min−1, min, min+1, max−1, max, max+1 (or the
   two-value variant if the team uses it). Add length boundaries for strings, and zero,
   negative and very large numbers where the type allows them.
4. **Decision table for combined rules** — one column per combination of conditions and the
   expected action per column; collapse impossible or equivalent columns and say why.
5. **Expected outcome for every value**, traced to the rule it checks.

## Output shape
```
## Input Design — age (integer, 18-60 inclusive, required)
Partitions: valid 18-60 · invalid <18 · invalid >60 · invalid non-integer · invalid empty
| Value | Partition | Expected | Rule |
|-------|-----------|----------|------|
| 17 | below range | rejected | min 18 |
| 18 | valid (min) | accepted | min 18, inclusive |
| 19 | valid | accepted | |
| 59 | valid | accepted | |
| 60 | valid (max) | accepted | max 60, inclusive |
| 61 | above range | rejected | max 60 |
| "" | empty | rejected | required |
| 25.5 | non-integer | rejected | integer |
--- HUMAN REVIEW GATE --- "Confirm the inclusive limits and the expected error messages"
```

## Guardrails
- Never guess whether a limit is inclusive; ask, because the boundary tests depend on it.
- Expected error messages come from the spec; if it has none, write "rejected" and flag it.
- Keep every value traceable to a rule; a value without a rule is noise.
