---
name: gatling-simulation-writer
description: >-
  Writes Gatling load-test simulations in the Java DSL (also usable from Kotlin or Scala). Use
  when an SDET says "write a Gatling simulation", "load test this API with Gatling", "add
  assertions on the 95th percentile", or works in a JVM project. Produces a simulation with
  the HTTP protocol, scenarios with checks and feeders, an open or closed injection profile,
  and global assertions that fail the build, run with Maven or Gradle.
license: MIT
metadata:
  author: AiTester
  pack: performance
  version: 1.0.0
---

# Gatling Simulation Writer

You write **load tests as code that fail the build when performance regresses** — readable
scenarios, realistic injection, assertions on percentiles.

## When to use
- A JVM team wants load tests in the same repository and build as the service.
- Someone needs HTML reports and percentile assertions from a code-based tool.

## Workflow
1. **Targets and workload** — from the performance plan: users or arrival rate, duration,
   p95 and error-rate limits. Ask if they are missing.
2. **Protocol** — `http.baseUrl(...)` with common headers, read from configuration.
3. **Scenario** — the user journey with `exec(http(...).get/post(...).check(...))`, `pause` for
   think time, and a `feed(...)` of test data from a CSV feeder.
4. **Injection** — open model (`rampUsers`, `constantUsersPerSec`) for arrival-driven
   traffic, or closed model (`constantConcurrentUsers`) for a fixed user pool.
5. **Assertions** — global response-time percentile and failed-request percentage.
6. **Run** — `mvn gatling:test` (or the Gradle plugin) and keep the HTML report as a CI artifact.

## Output shape
```java
import static io.gatling.javaapi.core.CoreDsl.*;
import static io.gatling.javaapi.http.HttpDsl.*;

import io.gatling.javaapi.core.*;
import io.gatling.javaapi.http.*;
import java.time.Duration;

public class OrdersSimulation extends Simulation {
  HttpProtocolBuilder httpProtocol = http.baseUrl(System.getProperty("baseUrl", "http://localhost:8080"))
      .acceptHeader("application/json");

  ScenarioBuilder browse = scenario("Browse orders")
      .exec(http("list orders").get("/api/orders?limit=20").check(status().is(200)))
      .pause(1, 3);

  {
    setUp(browse.injectOpen(rampUsers(100).during(Duration.ofMinutes(2))))
        .protocols(httpProtocol)
        .assertions(
            global().responseTime().percentile(95.0).lt(500),
            global().failedRequests().percent().lt(1.0));
  }
}
```

## Guardrails
- Targets in assertions come from agreed objectives, never from guesses.
- Do not run against production or shared environments without approval.
- Check the Gatling version's DSL before adopting the draft; APIs change between majors.
