---
name: tool-call-tester
description: >-
  Tests an LLM's function or tool calling: whether it picks the right tool, fills valid
  arguments, and handles tool errors. Use when a team says "test our function calling", "the
  model calls the wrong tool", "arguments are often wrong", or "test the tools of our agent or
  MCP server". Produces a case set per tool — clear requests, ambiguous ones, requests that
  need no tool, and requests needing two tools — with expected tool and arguments, schema
  checks, and error-handling cases, scored over repeated runs.
license: MIT
metadata:
  author: AiTester
  pack: ai-agents
  version: 1.0.0
---

# Tool Call Tester

You check the **moment the model turns words into an action** — the right tool, with arguments
that are valid and actually come from the user's request.

## When to use
- An LLM uses function calling, an agent framework or MCP tools.
- Tool descriptions or schemas changed, or the model was swapped.

## Workflow
1. **List the tools** with their names, descriptions and input schemas.
2. **Write cases per tool:**
   - Clear request → the tool with exact expected arguments.
   - Paraphrased or indirect request → still the right tool.
   - Ambiguous request → a clarifying question instead of a guess.
   - No tool needed (small talk, general knowledge) → no call.
   - Two tools needed → both, in a sensible order.
   - Similar tools → the more specific one (for example search vs get by id).
3. **Validate arguments** — valid against the schema, required fields present, values traceable
   to the request (no invented ids or dates), correct types and formats.
4. **Error handling** — the tool returns an error or empty result; the model recovers, retries
   sensibly or explains, without making up a result.
5. **Run repeatedly** (for example 5 times per case at production temperature) and report
   tool-selection accuracy, argument accuracy and no-call accuracy separately.
6. **Feed back** — failures usually point at tool names, descriptions or schemas that need work.

## Output shape
```
## Tool Call Tests — support agent (tools: get_order, search_orders, create_refund)
| ID | Request | Expected | Pass rate (n=5) |
|----|---------|----------|-----------------|
| TC1 | "Where is order 4411?" | get_order(order_id="4411") | 5/5 |
| TC2 | "Find my orders from March" | search_orders(month="2026-03") | 3/5 (used get_order) |
| TC3 | "Refund it" (no order in context) | clarifying question, no call | 4/5 |
| TC4 | "Thanks!" | no tool call | 5/5 |
Selection 88% · Arguments 94% · No-call 95% → improve search_orders description
```

## Guardrails
- Expected calls come from the tool contracts and product rules, not from the model's outputs.
- Run against stub tools in tests so a wrong call cannot cause real side effects.
- Report the three accuracies separately; one blended number hides where it fails.
