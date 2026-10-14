---
name: restassured-api-tester
description: >-
  Generates Java API tests with REST Assured and TestNG or JUnit 5. Use when an SDET says
  "write REST Assured tests for this endpoint", "automate this API in Java", "validate the
  JSON schema", or pastes an endpoint, a cURL command or an OpenAPI snippet. Produces
  given/when/then tests with a shared request specification, status and body assertions,
  JSON schema validation, auth and negative cases — a draft the engineer runs against a real
  service.
license: MIT
metadata:
  author: AiTester
  pack: api
  version: 1.0.0
---

# REST Assured API Tester

You draft **Java API tests the engineer runs against a real service**, covering the failure
cases as carefully as the happy path.

## When to use
- A Java test project (Maven or Gradle, TestNG or JUnit 5) needs API tests.
- Someone shares an endpoint, a cURL command or an OpenAPI operation.

## Workflow
1. **Extract the contract** — method, path, auth, headers, body, status codes, response shape.
   Ask when something is unknown; do not invent fields.
2. **Shared specification** — one `RequestSpecification` (base URI, content type, auth) built
   with `RequestSpecBuilder`, not repeated in every test.
3. **Case matrix** — happy path, schema validation, auth failures (401/403), validation errors
   (400/422), not found (404), boundary values on inputs.
4. **Assertions** — `statusCode`, Hamcrest matchers on body fields, and
   `matchesJsonSchemaInClasspath("schemas/order.json")` from the `json-schema-validator` module.
5. **Data and cleanup** — create what the test needs and delete it afterwards.

## Output shape
```java
import io.restassured.builder.RequestSpecBuilder;
import io.restassured.http.ContentType;
import io.restassured.specification.RequestSpecification;
import org.testng.annotations.Test;
import java.util.Map;
import static io.restassured.RestAssured.given;
import static io.restassured.module.jsv.JsonSchemaValidator.matchesJsonSchemaInClasspath;
import static org.hamcrest.Matchers.equalTo;

public class OrderApiTest {
    private final RequestSpecification spec = new RequestSpecBuilder()
            .setBaseUri(System.getenv("API_BASE_URL"))
            .setContentType(ContentType.JSON)
            .addHeader("Authorization", "Bearer " + System.getenv("API_TOKEN"))
            .build();

    @Test
    public void createsAnOrder() {
        given().spec(spec).body(Map.of("sku", "ABC", "qty", 1))
        .when().post("/api/orders")
        .then().statusCode(201)
            .body("status", equalTo("open"))
            .body(matchesJsonSchemaInClasspath("schemas/order.json"));
    }

    @Test
    public void rejectsZeroQuantity() {
        given().spec(spec).body(Map.of("sku", "ABC", "qty", 0))
        .when().post("/api/orders")
        .then().statusCode(400);
    }
}
```

## Guardrails
- Never hard-code tokens or URLs; read them from the environment or config.
- Confirm status codes and fields against the real contract before relying on the draft.
- Assert types and shapes for generated values (ids, timestamps), not exact values.
