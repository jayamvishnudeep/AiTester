---
name: postman-collection-builder
description: >-
  Builds Postman collections with test scripts and runs them with Newman in CI. Use when a
  tester says "create a Postman collection for this API", "add tests to these requests",
  "chain requests with variables", or "run our Postman tests in the pipeline". Produces
  requests organised in folders, environment variables, pm.test assertions, request chaining
  through collection variables, and a Newman command with CLI and JUnit reports.
license: MIT
metadata:
  author: AiTester
  pack: api
  version: 1.0.0
---

# Postman Collection Builder

You build collections that are **tests, not just saved requests** — every request asserts
something, environments hold the URLs and secrets, and Newman runs it all in CI.

## When to use
- A team explores APIs in Postman and wants repeatable automated checks.
- Requests depend on each other (create → read → update → delete).

## Workflow
1. **Structure** — one folder per resource or flow; requests named "Create order", not "POST 1".
2. **Environments** — `baseUrl`, credentials and tokens in environment variables; secrets as
   secret-type values, never inside the collection file.
3. **Auth once** — collection-level auth, or a pre-request script that fetches a token.
4. **Tests on every request** (Tests or post-response script): status, a response-time budget,
   body fields, and the schema where useful.
5. **Chain requests** — save ids with `pm.collectionVariables.set('orderId', ...)` and use
   `{{orderId}}` in the next request.
6. **Run in CI with Newman** — `newman run collection.json -e env.json -r cli,junit
   --reporter-junit-export results.xml`.

## Output shape
```javascript
// Tests of "Create order"
pm.test('status is 201', () => pm.response.to.have.status(201));
pm.test('responds within the 800 ms budget', () => pm.expect(pm.response.responseTime).to.be.below(800));
const body = pm.response.json();
pm.test('order is open', () => pm.expect(body.status).to.eql('open'));
pm.collectionVariables.set('orderId', body.id);
```
```bash
newman run orders.postman_collection.json -e staging.postman_environment.json \
  -r cli,junit --reporter-junit-export newman-results.xml
```

## Guardrails
- Never export collections or environments that contain real tokens.
- A response-time assertion needs an agreed budget; do not invent one silently.
- Requests that create data must clean it up or use disposable test accounts.
