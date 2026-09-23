# Security test plan — Shopfront Storefront API

**Authorised testing only.** These are OWASP-standard detection probes for an API you own or have explicit written permission to test - your own staging or QA environment. Running them against a system you do not have permission to test is unauthorised access in most jurisdictions, regardless of intent.

*Generated 2026-09-23. Every check below targets a parameter parsed from the spec at `e:/Visual Studio Code/AiTester/08_Automate_Daily_QA_Tasks_AI_Agents/02_Langflow_Agents/15_Security_Test_Generator_AI_Agent/sample_apis/shopfront_openapi.json` — re-run the mapper to reproduce it.*

## At a glance

| | |
|---|---|
| API | Shopfront Storefront API |
| Base URL | https://staging.shopfront.example.com/api/v1 |
| Endpoints | 11 |
| Parameters | 19 |
| **Checks to run** | **46** — 20 critical, 21 high, 5 medium |

## By category

| Category | Checks |
|---|---:|
| injection | 40 |
| access control | 3 |
| validation | 2 |
| ssrf | 1 |

---

## Where to start

*This section is written by a language model from the checks above. Every check it discusses is one code already found; it adds no new ones.*

**1. Run First: IDOR on Path Parameters**
Prioritize the Broken Object-Level Authorization (IDOR) checks on `GET /orders/{orderId}`, `GET /products/{productId}`, and `GET /users/{userId}`. These are critical severity. Unlike XSS, which requires user interaction to exploit, IDOR is a direct data breach. If the API lacks proper ownership validation, an attacker can enumerate IDs to access other users’ private orders, financial data, or PII. The likelihood of this bug is high in REST APIs where path parameters are used for resource identification without strict session-boundary enforcement. A single finding here compromises the entire trust model of the platform.

**2. Run Last/Skip: XSS on Display Fields**
Defer or skip Reflected XSS checks on `displayName` in `POST /reviews` and `q` in `GET /products`. While listed as high severity, reflected XSS is generally lower impact than data exfiltration or system compromise. It requires a victim to click a crafted link, and modern frameworks often auto-escape output. Given limited time, the probability of a successful, high-impact exploit here is lower than the certainty of data leakage via IDOR. Similarly, skip the `Authorization` header CRLF check on `GET /orders/{orderId}`; header injection is rare in modern API gateways and has minimal impact compared to the critical IDOR risk on the same endpoint.

**3. Structural Risk: Systemic Lack of Input Validation**
The surface shows a pervasive pattern: nearly every endpoint, from `/login` to `/files/download`, lists SQL injection as a critical check. This suggests the API may rely on string concatenation for database queries rather than parameterized statements across the entire stack. If one endpoint is vulnerable, it is highly probable that others are too. This systemic weakness means a single successful SQLi payload could potentially bypass authentication, dump the entire database, or execute arbitrary commands, making it a far greater structural threat than any single parameter’s specific vulnerability.

---

## Every check, grouped by endpoint

### GET /products

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `q` | query | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `category` | query | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `sort` | query | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `page` | query | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `q` | query | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `category` | query | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `sort` | query | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |

- **SQL injection on `q`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `q`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **SQL injection on `category`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `category`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **SQL injection on `sort`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `sort`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **SQL injection on `page`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.

### GET /products/{productId}

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `productId` | path | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `productId` | path | Broken object-level authorization (IDOR) | A01:2021 Broken Access Control / API1:2023 / WSTG-ATHZ-04 | CRITICAL | `<the id of an object belonging to another user>`  `1`  `0`  `-1`  `<a valid id you were not given>` |

- **SQL injection on `productId`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Broken object-level authorization (IDOR) on `productId`** — look for: You receive an object that belongs to a different user or account than yours.
    Note: This is an access-control check, not an injection - do not send injection strings, change the identifier to one you should not be able to see.
    Fix if found: Check on every request that the authenticated user owns the object.

### GET /users/{userId}

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `userId` | path | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `userId` | path | Broken object-level authorization (IDOR) | A01:2021 Broken Access Control / API1:2023 / WSTG-ATHZ-04 | CRITICAL | `<the id of an object belonging to another user>`  `1`  `0`  `-1`  `<a valid id you were not given>` |

- **SQL injection on `userId`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Broken object-level authorization (IDOR) on `userId`** — look for: You receive an object that belongs to a different user or account than yours.
    Note: This is an access-control check, not an injection - do not send injection strings, change the identifier to one you should not be able to see.
    Fix if found: Check on every request that the authenticated user owns the object.

### GET /orders/{orderId}

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `orderId` | path | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `orderId` | path | Broken object-level authorization (IDOR) | A01:2021 Broken Access Control / API1:2023 / WSTG-ATHZ-04 | CRITICAL | `<the id of an object belonging to another user>`  `1`  `0`  `-1`  `<a valid id you were not given>` |
| `Authorization` | header | HTTP header / CRLF injection | A03:2021 Injection / WSTG-INPV-16 | MEDIUM | `%0d%0aX-Injected:%201`  `%0d%0aSet-Cookie:%20injected=1`  `
X-Injected: 1` |

- **SQL injection on `orderId`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Broken object-level authorization (IDOR) on `orderId`** — look for: You receive an object that belongs to a different user or account than yours.
    Note: This is an access-control check, not an injection - do not send injection strings, change the identifier to one you should not be able to see.
    Fix if found: Check on every request that the authenticated user owns the object.
- **HTTP header / CRLF injection on `Authorization`** — look for: The injected header (X-Injected, Set-Cookie) appears in the response headers.
    Fix if found: Strip CR and LF from anything written into a header.

### POST /login

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `username` | body | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `password` | body | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `username` | body | NoSQL injection | A03:2021 Injection / WSTG-INPV-05 | HIGH | `{"$ne": null}`  `{"$gt": ""}`  `{"$regex": ".*"}`  `' || '1'=='1` |
| `username` | body | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `username` | body | Server-side template injection | A03:2021 Injection / WSTG-INPV-18 | HIGH | `${7*7}`  `{{7*7}}`  `#{7*7}`  `<%= 7*7 %>`  `${{7*7}}` |
| `username` | body | LDAP injection | A03:2021 Injection / WSTG-INPV-06 | HIGH | `*`  `*)(uid=*`  `admin)(&)`  `*)(|(uid=*`  `*))%00` |
| `password` | body | NoSQL injection | A03:2021 Injection / WSTG-INPV-05 | HIGH | `{"$ne": null}`  `{"$gt": ""}`  `{"$regex": ".*"}`  `' || '1'=='1` |
| `password` | body | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |

- **SQL injection on `username`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **NoSQL injection on `username`** — look for: Authentication bypassed, or records returned that a plain value would not match.
    Fix if found: Validate types server-side; reject objects where a scalar is expected.
- **Reflected cross-site scripting on `username`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **Server-side template injection on `username`** — look for: The number 49 appears in the response where 7*7 was evaluated.
    Fix if found: Never build a template from user input; pass it as data to a fixed template.
- **LDAP injection on `username`** — look for: Authentication bypassed, or more directory entries returned than a real value matches.
    Fix if found: Escape LDAP special characters; use a parameterised directory query.
- **SQL injection on `password`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **NoSQL injection on `password`** — look for: Authentication bypassed, or records returned that a plain value would not match.
    Fix if found: Validate types server-side; reject objects where a scalar is expected.
- **Reflected cross-site scripting on `password`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.

### POST /reviews

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `productId` | body | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `comment` | body | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `displayName` | body | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `comment` | body | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `comment` | body | Server-side template injection | A03:2021 Injection / WSTG-INPV-18 | HIGH | `${7*7}`  `{{7*7}}`  `#{7*7}`  `<%= 7*7 %>`  `${{7*7}}` |
| `displayName` | body | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `displayName` | body | Server-side template injection | A03:2021 Injection / WSTG-INPV-18 | HIGH | `${7*7}`  `{{7*7}}`  `#{7*7}`  `<%= 7*7 %>`  `${{7*7}}` |

- **SQL injection on `productId`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **SQL injection on `comment`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `comment`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **Server-side template injection on `comment`** — look for: The number 49 appears in the response where 7*7 was evaluated.
    Fix if found: Never build a template from user input; pass it as data to a fixed template.
- **SQL injection on `displayName`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `displayName`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **Server-side template injection on `displayName`** — look for: The number 49 appears in the response where 7*7 was evaluated.
    Fix if found: Never build a template from user input; pass it as data to a fixed template.

### GET /files/download

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `path` | query | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `path` | query | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `path` | query | Path traversal | A01:2021 Broken Access Control / WSTG-ATHZ-01 | HIGH | `../../../../etc/passwd`  `..\..\..\..\windows\win.ini`  `....//....//....//etc/passwd`  `%2e%2e%2f%2e%2e%2fetc%2fpasswd`  `/etc/passwd` |

- **SQL injection on `path`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `path`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **Path traversal on `path`** — look for: File contents that are not the intended file - root:x:0:0 from /etc/passwd, or the [fonts] section of win.ini.
    Fix if found: Resolve to a canonical path and confirm it stays inside the allowed root.

### POST /integrations/webhook

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `url` | body | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `event` | body | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `url` | body | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `url` | body | Server-side request forgery | A10:2021 SSRF / WSTG-INPV-19 | HIGH | `http://169.254.169.254/latest/meta-data/`  `http://127.0.0.1:22`  `http://localhost/`  `file:///etc/passwd`  `http://[::1]/` |
| `event` | body | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `url` | body | Open redirect | A01:2021 Broken Access Control / WSTG-CLNT-04 | MEDIUM | `//evil.example.com`  `https://evil.example.com`  `/\evil.example.com`  `https:evil.example.com`  `javascript:alert(1)` |
| `url` | body | HTTP header / CRLF injection | A03:2021 Injection / WSTG-INPV-16 | MEDIUM | `%0d%0aX-Injected:%201`  `%0d%0aSet-Cookie:%20injected=1`  `
X-Injected: 1` |

- **SQL injection on `url`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `url`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **Server-side request forgery on `url`** — look for: Cloud metadata, an internal service banner, or a timing difference between a reachable internal host and an unreachable one.
    Fix if found: Allow-list destinations; block link-local, loopback and private ranges.
- **Open redirect on `url`** — look for: A 3xx response whose Location header points at evil.example.com.
    Fix if found: Redirect only to a relative path or an allow-listed host.
- **HTTP header / CRLF injection on `url`** — look for: The injected header (X-Injected, Set-Cookie) appears in the response headers.
    Fix if found: Strip CR and LF from anything written into a header.
- **SQL injection on `event`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `event`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.

### GET /auth/callback

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `code` | query | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `next` | query | SQL injection | A03:2021 Injection / WSTG-INPV-05 | CRITICAL | `'`  `' OR '1'='1`  `' OR '1'='1' -- `  `1 OR 1=1`  `' UNION SELECT NULL-- ` |
| `code` | query | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `next` | query | Reflected cross-site scripting | A03:2021 Injection / WSTG-INPV-01 | HIGH | `<script>alert(1)</script>`  `"><script>alert(1)</script>`  `<img src=x onerror=alert(1)>`  `'"><svg onload=alert(1)>`  `javascript:alert(1)` |
| `next` | query | Open redirect | A01:2021 Broken Access Control / WSTG-CLNT-04 | MEDIUM | `//evil.example.com`  `https://evil.example.com`  `/\evil.example.com`  `https:evil.example.com`  `javascript:alert(1)` |
| `next` | query | HTTP header / CRLF injection | A03:2021 Injection / WSTG-INPV-16 | MEDIUM | `%0d%0aX-Injected:%201`  `%0d%0aSet-Cookie:%20injected=1`  `
X-Injected: 1` |

- **SQL injection on `code`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `code`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **SQL injection on `next`** — look for: A database error in the response, a 500, results that change between ' OR '1'='1 and ' OR '1'='2, or a ~5s delay on the SLEEP / WAITFOR probe.
    Fix if found: Use parameterised queries; never build SQL by string concatenation.
- **Reflected cross-site scripting on `next`** — look for: The payload comes back in the response body unencoded - the < and > are still angle brackets, not &lt; and &gt;.
    Fix if found: Context-encode on output; set a Content-Security-Policy.
- **Open redirect on `next`** — look for: A 3xx response whose Location header points at evil.example.com.
    Fix if found: Redirect only to a relative path or an allow-listed host.
- **HTTP header / CRLF injection on `next`** — look for: The injected header (X-Injected, Set-Cookie) appears in the response headers.
    Fix if found: Strip CR and LF from anything written into a header.

### POST /catalog/import

| Param | In | Attack | OWASP | Severity | Payloads to try |
|---|---|---|---|---|---|
| `<xml body>` | body | XML external entity | A05:2021 Security Misconfiguration / WSTG-INPV-07 | HIGH | `<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>`  `<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "http://169.254.169.254/">]><r>&x;</r>` |

- **XML external entity on `<xml body>`** — look for: File contents (root:x:0:0) or an internal response reflected back inside the parsed XML.
    Fix if found: Disable external entity and DTD processing in the XML parser.

## No injectable parameters found

These endpoints take no parameters this mapper checks, or take none at all. That is not the same as secure - it means this pass has nothing further to add:

- GET /status

---

## What this plan does not cover

This maps OWASP injection and access-control checks from the shape of the API alone - it has not run anything. It does not cover business-logic flaws, authentication design, rate limiting, or anything that needs the running application rather than its interface to evaluate. Executing these checks, and confirming a positive signal against the running API, is still a human step.
