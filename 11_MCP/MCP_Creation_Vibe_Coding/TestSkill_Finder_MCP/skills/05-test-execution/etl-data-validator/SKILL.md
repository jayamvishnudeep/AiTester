---
name: etl-data-validator
description: >-
  Validate ETL and data pipelines: source-to-target completeness, correctness and quality.
  Use when a tester says "test this ETL job", "did all records load", "validate the data
  warehouse", "reconcile source and target", or shares mapping documents or SQL for a
  pipeline. Produces reconciliation checks (row counts, sums, checksums), transformation rule
  tests from the mapping document, data quality checks (nulls, duplicates, ranges, referential
  integrity), and incremental-load and rejected-record checks.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Execution
  version: 1.0.0
---

# ETL Data Validator

You prove that **what arrived is what was sent, transformed exactly as specified** — with
numbers that reconcile, not a glance at a dashboard.

## When to use
- A pipeline, ETL job, data migration or warehouse load needs testing.
- Reports disagree with the source system and someone needs to find where data changed.

## Workflow
1. **Get the mapping document** — source fields, target fields, transformation rules, filters,
   keys, load type (full or incremental). Without it, ask; do not reverse-engineer rules from
   the data.
2. **Completeness** — row counts per load and partition: source = target + rejected + filtered
   (each with its reason).
3. **Correctness** — per transformation rule, compare source and target values for a sample
   and for edge cases (nulls, maximum lengths, special characters, time zones); totals of
   numeric columns (SUM, MIN, MAX) reconcile.
4. **Data quality** — no duplicate business keys, NOT NULL fields filled, values in range,
   foreign keys resolve, slowly changing dimensions keep history as designed.
5. **Incremental loads** — only new or changed rows load; re-running the job does not duplicate
   data (idempotence); late-arriving records are handled.
6. **Rejected records** — invalid rows land in the reject or error table with a reason.

## Output shape
```sql
-- E1 completeness: source vs target row count for the load date
SELECT (SELECT COUNT(*) FROM src.orders WHERE order_date = :d) AS source_rows,
       (SELECT COUNT(*) FROM dw.fact_orders WHERE order_date = :d) AS target_rows,
       (SELECT COUNT(*) FROM dw.rejected_orders WHERE order_date = :d) AS rejected_rows;
-- expect source_rows = target_rows + rejected_rows

-- E2 duplicate business keys in the target (expect 0 rows)
SELECT order_id, COUNT(*) FROM dw.fact_orders GROUP BY order_id HAVING COUNT(*) > 1;
```

## Guardrails
- Every expected value comes from the mapping document or the source data, never from guesses.
- Report counts and the query used; "looks right" is not a result.
- Run validations on test or staging copies; do not load test data into production tables.
