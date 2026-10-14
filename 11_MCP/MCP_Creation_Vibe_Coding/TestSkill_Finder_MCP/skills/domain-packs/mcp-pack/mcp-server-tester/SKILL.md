---
name: mcp-server-tester
description: >-
  Tests an MCP server's tools, resources and prompts through the protocol, the way a client
  sees them. Use when an engineer says "test my MCP server", "write tests for these MCP
  tools", "verify the tool schemas", or "check the server before we share it". Produces
  automated tests with an in-memory or HTTP client (list and call every tool, valid and
  invalid inputs, error results, annotations, resources and prompts), CLI smoke checks with
  `fastmcp list` and `fastmcp call`, and a manual MCP Inspector checklist.
license: MIT
metadata:
  author: AiTester
  pack: mcp
  version: 1.0.0
---

# MCP Server Tester

You test the server **through MCP itself** — the schemas, results and errors a client receives —
not only the Python functions behind it.

## When to use
- An MCP server is about to be shared or deployed.
- Tools work in a quick demo but nobody has checked edge cases, errors or schemas.

## Workflow
1. **Inventory** — `fastmcp list server.py --resources --prompts --input-schema` (or the
   server's URL) shows what a client will see; check names, descriptions and schemas.
2. **Automated tests with a client** — FastMCP's `Client(server)` connects in memory (no
   network); with pytest-asyncio, every test lists or calls through MCP.
3. **For every tool** — a valid call (check the structured result), each invalid input
   (out-of-range values, wrong enum, missing required field) returning an error result, and the
   documented example input running as written.
4. **Errors** — tool failures come back as error results with a helpful message, not crashes or
   stack traces; protocol errors only for protocol problems.
5. **Annotations and tags** — read-only tools marked read-only, writing tools not; any
   profile that hides tools really hides them.
6. **Resources and prompts** — every resource URI and template resolves; unknown ids fail
   cleanly; prompts render with their arguments.
7. **Manual pass in MCP Inspector** — connect over the real transport, run each tool once, and
   check the client's view of descriptions and errors.

## Output shape
```python
import pytest
from fastmcp import Client
from my_server import mcp

async def test_every_tool_is_listed_with_a_description():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert {t.name for t in tools} >= {"get_order", "search_orders"}
        assert all(t.description for t in tools)

async def test_unknown_order_is_an_error_result():
    async with Client(mcp) as client:
        result = await client.call_tool("get_order", {"order_id": "nope"}, raise_on_error=False)
        assert result.is_error and "search_orders" in result.content[0].text
```
```bash
fastmcp call server.py get_order order_id=4411
```

## Guardrails
- Point tests at test data or stub backends; tool calls in tests must not change real systems.
- Test the documented examples; a broken example teaches every client the wrong call.
- Re-run the suite after upgrading the MCP SDK; protocol details change between versions.
