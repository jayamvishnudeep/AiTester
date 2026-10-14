---
name: database-test-designer
description: >-
  Design database tests: schema, constraints, data integrity, stored logic and migrations.
  Use when a tester says "test the database side of this feature", "validate the data after
  this API call", "test this migration", "check constraints and triggers", or shares a schema,
  SQL or an ER diagram. Produces SQL checks for constraints (keys, unique, not null, foreign
  keys), CRUD side effects, transactions and rollback, stored procedures and triggers, and
  before/after migration comparisons — run against test databases only.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Design
  version: 1.0.0
---

# Database Test Designer

You test **what the UI cannot show** — whether the data that lands in the database is correct,
consistent and protected by the right constraints.

## When to use
- A feature writes, updates or deletes data and the UI only shows part of it.
- A schema migration, stored procedure, trigger or batch job changes data.

## Workflow
1. **Read the schema** — tables, keys, constraints, indexes, triggers, procedures involved.
   Ask for the DDL or an ER diagram instead of guessing column names.
2. **Constraint tests** — inserting duplicates on unique keys, nulls in NOT NULL columns,
   orphans against foreign keys, out-of-range values against CHECK constraints: each must be
   rejected.
3. **CRUD side effects** — after an API or UI action, query the affected rows: values,
   defaults, timestamps, audit columns, soft-delete flags, and that nothing else changed.
4. **Transactions** — a failure midway rolls everything back; concurrent updates do not lose
   writes (two sessions updating the same row).
5. **Stored logic** — procedures and triggers with normal, boundary and invalid inputs.
6. **Migrations** — row counts, checksums or sampled comparisons before and after; new columns
   populated correctly; rollback script tested.

## Output shape
```sql
-- D1: order total equals the sum of its lines (after "place order")
SELECT o.id, o.total, SUM(l.qty * l.unit_price) AS lines_total
FROM orders o JOIN order_lines l ON l.order_id = o.id
WHERE o.id = :order_id
GROUP BY o.id, o.total
HAVING o.total <> SUM(l.qty * l.unit_price);   -- expect 0 rows

-- D2: email must be unique (expect a unique-constraint error)
INSERT INTO users (email) VALUES ('dup@example.test');
INSERT INTO users (email) VALUES ('dup@example.test');
```

## Guardrails
- Run against test databases only; never run write tests against production.
- Use test-owned data and clean it up, or wrap checks in a transaction that rolls back.
- Never invent table or column names; ask for the schema.
