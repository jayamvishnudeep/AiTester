# Plan — Security Test Generator (Langflow AI Agent)

| | |
|---|---|
| **Role** | Security QA |
| **Problem** | QA lacks security testing expertise |
| **Input** | An API endpoint or its documentation |
| **Output** | A list of OWASP injection attack vectors |
| **Shape** | Text Input → Prompt Template → LLM → Structured Output → Text Output |

## What this agent is, plainly

This generates **detection probes** — the standard published OWASP strings a
scanner sends to reveal whether a class of vulnerability exists — for an API a
functional QA is authorized to test. It is defensive: the intended use is a
tester running these against their own staging environment because their team
does not have a dedicated security engineer.

Every report opens with the same line, in bold, before anything else: test only
what you have permission to test. That is not boilerplate the model was asked
to write; it is a fixed string composed into every report regardless of what
the model says, so it cannot be prompted away.

## Why the payloads are a catalog, not a generation

The given shape ends in an LLM producing structured output - the model deciding
what a SQL injection payload looks like, freehand, for a given field. That is
the wrong place to put a decision, for a reason specific to this agent: **an
invented injection string is a live security-testing action with no reviewer**,
in a way an invented test case or an invented selector is not.

So the payloads are a fixed, hand-verified catalog of the OWASP testing guide's
own reference strings - `' OR '1'='1`, `<script>alert(1)</script>`,
`../../../../etc/passwd`, `http://169.254.169.254/latest/meta-data/` - and the
model never writes one. Its only decision is which parameter, among the ones
code already matched, is worth trying first. That containment is also why every
payload in the catalog is checked to be non-destructive: nothing writes, deletes
or corrupts, because every payload's job is to *reveal* a class of bug, not use
it.

## Why the attack surface is parsed, never guessed

The second risk this agent carries is different from the others in the
section: **a false positive here is a tester's afternoon**, not a build that
ships broken. A security report telling someone to try SQL injection on a
parameter the endpoint does not have sends them looking for something that
cannot be found, and erodes trust in the parts of the report that were real.

So the mapper reads the actual spec - OpenAPI JSON, OpenAPI YAML, or a plain
`METHOD /path?param=` list when there is no formal spec - and every vector in
the output traces to a parameter it found there. The model receives the mapped
surface as a brief and is told explicitly not to add a check, an endpoint or a
parameter that is not in it; the writer verifies the model's prose actually
references a real endpoint rather than talking in generalities, and flags it
when it does not.

## Targeting, not a template stamped on every field

The naive version of this agent offers every attack class on every field. That
produces a report nobody reads twice, and reading a security report twice is
the whole value of getting the first pass right.

So each attack class carries its own applicability rule, matched against the
parameter's name, its location (query, path, body, header) and its type:

- **SSRF, open redirect and CRLF** only fire on a parameter shaped like a URL,
  a callback, a redirect target or a header.
- **Path traversal** only fires on something shaped like a file path.
- **XXE** only fires on a parameter that is literally an XML request body.
- **BOLA (IDOR)** only fires on an id carried in the path or the query, because
  that is the shape an object reference actually takes.
- **SQL injection and XSS** are broad on purpose - almost any string or integer
  input can carry either, and narrowing them would create the false negative
  this agent cannot afford.

BOLA earns its place despite not being an injection attack: it is the top risk
in the OWASP API Security Top 10, and a QA testing only injection would miss
the single most common real-world API bug. It can be turned off for an
injection-only report.

## Pipeline

```
Text Input (API spec path)
  → Attack Surface Mapper   parse OpenAPI JSON/YAML or a plain endpoint list,
                            find every real parameter, match each to its
                            applicable attack classes and payloads, write
                            attack_surface.json
  → Prompt Template         the mapped surface: every endpoint, parameter,
                            check, severity and payload already computed
  → Groq                    orders the checks by real-world risk; forbidden
                            to add a check, endpoint or parameter
  → Security Test Plan Writer   fixed disclaimer first, then the computed
                            checks in full, then the model's prioritisation,
                            then what the plan does not cover
  → Chat Output
```

## Verified

- **139 component tests**, no Langflow or network needed. The largest single
  group checks that every attack class fires only where it plausibly applies -
  SSRF on a URL-shaped parameter and nowhere else, path traversal on a
  file-shaped one, XXE only on an XML body, BOLA only on an id - and does not
  fire where it should not.
- **Every payload in the catalog is checked to be non-destructive** - no
  `DROP TABLE`, no `rm`, no write or delete, against a list of destructive
  patterns the test suite scans the whole catalog for.
- **Mutation-checked, ten defects.** Loosening a matcher to accept any
  parameter, letting the access-control toggle be ignored, and - the one that
  matters most for this particular agent - **removing the authorised-testing
  disclaimer** were each introduced alone and the suite went red for every one.
- **All three sample specs run end to end** through the real flow, and the
  counts in the README are the ones it produced.
- **Canvas edge count re-checked after opening in the UI** — five of five.

## What this is not

It does not run the checks. It does not confirm a finding. It does not replace
a security engineer or a real DAST/SAST tool - it is the thing a functional QA
runs before either of those exist on their team, to turn "we should probably
check for SQL injection" into a list with real parameters, real payloads, and a
sentence on what a hit would look like.
