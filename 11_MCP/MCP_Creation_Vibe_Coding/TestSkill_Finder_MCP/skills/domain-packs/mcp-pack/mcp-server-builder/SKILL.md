---
name: mcp-server-builder
description: >-
  Scaffolds a Model Context Protocol (MCP) server with tools, resources and prompts, ready to
  test. Use when an engineer says "build an MCP server for this", "expose our API or data as
  MCP tools", "create an MCP server with FastMCP", or "make this available to Claude or
  Cursor". Produces a FastMCP (Python) server — or the equivalent with the TypeScript SDK —
  with typed tools, descriptions that include example inputs, read-only annotations,
  resources and prompts, stdio and Streamable HTTP transports, and in-memory tests.
license: MIT
metadata:
  author: AiTester
  pack: mcp
  version: 1.0.0
---

# MCP Server Builder

You build **an MCP server an LLM can use correctly on the first try** — small focused tools,
clear descriptions with examples, and tests from day one.

## When to use
- Data, an API or a workflow should be callable from Claude, Cursor, VS Code or any MCP client.
- A prototype server exists but has no tests, vague tool descriptions or no HTTP transport.

## Workflow
1. **List the jobs** users will ask for; each becomes one tool with one purpose (verb_noun names
   such as `search_skills`, `get_order`).
2. **Type every parameter** — `Annotated[..., Field(description=..., ge=..., le=...)]` and
   `Literal` or Enum for fixed choices, so the input schema itself prevents bad calls.
3. **Describe each tool** — what it returns, when to use it, and one example input in JSON.
4. **Return structured output** — Pydantic models or dataclasses give an output schema;
   raise `ToolError` with an actionable message for bad input.
5. **Annotate** — read-only and idempotent hints for tools that only read; tags to group tools.
6. **Add resources and prompts** — read-only data by URI (`skills://catalog`), and prompt
   templates for common tasks.
7. **Transports** — stdio for a local client; Streamable HTTP (`/mcp`) to share one server.
8. **Test** with the in-memory client, then in MCP Inspector.

## Output shape
```python
from typing import Annotated
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

mcp = FastMCP("Orders", instructions="Look up orders. Start with search_orders.")

@mcp.tool(annotations={"readOnlyHint": True}, tags={"read"})
def get_order(order_id: Annotated[str, Field(description="Order id, e.g. '4411'")]) -> dict:
    """One order by id.

    Example input: {"order_id": "4411"}
    """
    order = ORDERS.get(order_id)
    if order is None:
        raise ToolError(f"No order {order_id}. Use search_orders to find ids.")
    return order

if __name__ == "__main__":
    mcp.run()  # stdio; mcp.run(transport="http", port=8000) serves http://127.0.0.1:8000/mcp
```

## Guardrails
- Keep secrets in environment variables, never in tool code or descriptions.
- Tools that change data need clear names, confirmation in the client, and no read-only hint.
- Check the SDK version's API before adopting the draft; MCP SDKs change between majors.
