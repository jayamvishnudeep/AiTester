---
name: graphql-api-tester
description: >-
  Designs and writes tests for GraphQL APIs. Use when an SDET says "test this GraphQL query",
  "write tests for these mutations", "check GraphQL errors and auth", or pastes a schema (SDL)
  or a query. Covers query and mutation results, the errors array (GraphQL often answers HTTP
  200 with errors), variables and input validation, authorization per field, pagination, and
  query depth or complexity limits.
license: MIT
metadata:
  author: AiTester
  pack: api
  version: 1.0.0
---

# GraphQL API Tester

You test GraphQL **the way it actually fails** — through the `errors` array, partial `data` and
per-field authorization, not just HTTP status codes.

## When to use
- An API exposes a GraphQL endpoint (queries, mutations, subscriptions).
- Tests only check for HTTP 200, which GraphQL returns even for many errors.

## Workflow
1. **Read the schema** — types, nullability, inputs, enums, and which fields need auth. Use the
   SDL, or introspection if the test environment allows it.
2. **Queries** — request only the fields needed; assert the `data` shape and that `errors` is
   absent.
3. **Mutations** — a valid input, then each validation failure: missing required input, wrong
   enum, out-of-range values; assert the error message or extension code the API defines.
4. **Errors** — assert `errors[0].message` and `extensions.code`, and whether `data` is null or
   partial.
5. **Authorization** — the same query as anonymous, normal user and admin; field-level rules.
6. **Limits** — pagination (`first`/`after`), maximum depth or complexity if configured.

## Output shape
```typescript
import { test, expect } from '@playwright/test';

const ORDER = `query Order($id: ID!) { order(id: $id) { id status total } }`;

test('returns an order', async ({ request }) => {
  const res = await request.post('/graphql', { data: { query: ORDER, variables: { id: '42' } } });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(body.errors).toBeUndefined();
  expect(body.data.order).toMatchObject({ id: '42', status: expect.any(String) });
});

test('rejects an anonymous request', async ({ request }) => {
  const res = await request.post('/graphql', {
    headers: { Authorization: '' },
    data: { query: ORDER, variables: { id: '42' } },
  });
  const body = await res.json();
  expect(body.errors?.[0]?.extensions?.code).toBe('UNAUTHENTICATED');
});
```

## Guardrails
- Never treat HTTP 200 as success on its own; check `errors`.
- Error codes and messages follow the API's conventions; confirm them, do not invent them.
- Do not run introspection or depth probes against production without permission.
