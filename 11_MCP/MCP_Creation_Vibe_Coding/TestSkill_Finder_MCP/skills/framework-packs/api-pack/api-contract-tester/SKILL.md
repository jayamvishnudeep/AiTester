---
name: api-contract-tester
description: >-
  Tests API contracts between consumers and providers with Pact or OpenAPI schema
  validation. Use when a team says "add contract tests", "stop breaking the frontend when the
  API changes", "validate responses against our OpenAPI spec", or "set up consumer-driven
  contracts". Produces consumer tests that record expectations, provider verification steps,
  and schema checks against the OpenAPI document, with guidance on where contract tests sit
  next to end-to-end tests.
license: MIT
metadata:
  author: AiTester
  pack: api
  version: 1.0.0
---

# API Contract Tester

You catch **breaking API changes before deployment** by testing the agreement between consumer
and provider, not the whole system.

## When to use
- Several services or a frontend depend on an API that changes often.
- End-to-end tests are slow and still miss "field renamed" or "type changed" breaks.
- An OpenAPI document exists and the real responses drift from it.

## Workflow
1. **Choose the approach**
   - Consumer-driven (Pact): each consumer records the requests it makes and the parts of the
     response it relies on; the provider verifies those pacts in its own pipeline.
   - Schema-based: validate real responses against the OpenAPI schema (an OpenAPI validator,
     or JSON Schema / Zod schemas generated from the document).
2. **Consumer side** — define interactions: provider state, request, and the minimal expected
   response using matchers (types and formats, not exact values).
3. **Share the contract** — publish pacts to a Pact Broker (or PactFlow) with versions and
   branches.
4. **Provider side** — verify against the running provider, with state handlers that set up
   each "given" state; fail the build on a mismatch.
5. **Gate deployment** — `can-i-deploy` with Pact, or schema validation as a CI step.

## Output shape
```typescript
// consumer test — @pact-foundation/pact (PactV3)
import { PactV3, MatchersV3 } from '@pact-foundation/pact';

const provider = new PactV3({ consumer: 'web-app', provider: 'orders-api' });

it('gets an order', () => {
  provider
    .given('order 42 exists')
    .uponReceiving('a request for order 42')
    .withRequest({ method: 'GET', path: '/orders/42' })
    .willRespondWith({
      status: 200,
      body: MatchersV3.like({ id: '42', status: 'open', total: 19.99 }),
    });
  return provider.executeTest(async (mockServer) => {
    const order = await getOrder(mockServer.url, '42');
    expect(order.status).toBe('open');
  });
});
```

## Guardrails
- Expect only the fields the consumer really uses; over-specified contracts break needlessly.
- Use type matchers for generated values, never exact ids or timestamps.
- Contract tests do not prove business behaviour; keep functional API tests for that.
