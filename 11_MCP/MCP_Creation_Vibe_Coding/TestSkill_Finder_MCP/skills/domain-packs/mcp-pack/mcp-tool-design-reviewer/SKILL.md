---
name: mcp-tool-design-reviewer
description: >-
  Reviews MCP tool design for how well LLMs can use the tools. Use when an engineer says
  "review our MCP tools", "the model keeps calling the wrong tool", "improve these tool
  descriptions", or "do we have too many tools". Checks names, descriptions, parameter schemas,
  defaults, limits, output size, error messages and annotations, finds overlapping or missing
  tools, and proposes concrete rewrites — since tool names and descriptions are effectively
  prompts for the model.
license: MIT
metadata:
  author: AiTester
  pack: mcp
  version: 1.0.0
---

# MCP Tool Design Reviewer

You review tools **from the model's point of view**: it sees only names, descriptions and schemas,
so those decide whether it calls the right tool with the right arguments.

## When to use
- An MCP server's tools are often misused, ignored or confused with each other.
- A server is about to be shared and its tools were never reviewed.

## Workflow
1. **List the tools** with names, descriptions, input schemas, output shapes and annotations.
2. **Names** — verb_noun, specific, consistent (`search_orders`, `get_order`, not `orders2`).
3. **Descriptions** — what it returns, when to use it instead of similar tools, important
   limits, and one example input. Front-load the key sentence.
4. **Parameters** — each described, with types, enums for fixed choices, sensible defaults,
   ranges (`limit` 1-100) and units; few required parameters.
5. **Outputs** — compact by default, paging for long lists (`total`, `next_offset`), structured
   rather than prose, no huge blobs that fill the context.
6. **Errors** — say what was wrong and what to do next ("Unknown module 'Funels'. Did you mean
   Funnels?").
7. **The set** — overlapping tools merged or clearly separated, missing jobs added, and the total
   kept small enough to choose from (group with tags or profiles if large).
8. **Annotations** — read-only and destructive hints set correctly.

## Output shape
```
## Tool Design Review — orders-mcp (9 tools)
| Tool | Issue | Proposed change |
|------|-------|-----------------|
| find | vague name; overlaps search_orders | rename to get_order_by_number or remove |
| search_orders | no limit; returns 5,000 rows | add limit (1-100, default 20) and next_offset |
| create_refund | no example; missing destructive hint | add example input; destructiveHint: true |
Missing: a tool to list valid order statuses (the model guesses them)
Rewrite of search_orders description: "Orders matching filters, newest first. Use get_order
when you already know the id. Example input: {\"status\": \"shipped\", \"limit\": 10}"
```

## Guardrails
- Base findings on real failures or the schemas themselves, not on taste.
- Keep breaking changes (renames, removed tools) in a migration note for existing clients.
- Re-test tool selection after changes (see the tool-call tester skill).
