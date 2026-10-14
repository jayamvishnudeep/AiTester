---
name: mcp-inspector-debugger
description: >-
  Debugs MCP server connections and calls with MCP Inspector. Use when an engineer says "my
  MCP server won't connect", "the Inspector shows an error", "tools don't show up", "invalid
  request when I open the URL", or "it works in one client but not another". Walks through
  transport (stdio, Streamable HTTP, legacy SSE), URL and path, start-up command, stdout
  pollution, authentication, timeouts and Windows quirks, and reads the protocol messages to
  find the failing step.
license: MIT
metadata:
  author: AiTester
  pack: mcp
  version: 1.0.0
---

# MCP Inspector Debugger

You find **which step of the MCP handshake fails** — start-up, transport, initialize, list or call
— and fix that step instead of guessing.

## When to use
- A server does not connect, or connects but shows no tools, or calls fail.
- A server works in one client (Claude Code, Cursor, VS Code, Inspector) but not another.

## Workflow
1. **Start the Inspector** — `npx @modelcontextprotocol/inspector`, or `fastmcp dev inspector
   server.py` for FastMCP servers; note the URL and token it prints.
2. **Match the transport** — stdio (the Inspector starts the command), Streamable HTTP (a URL,
   usually ending in `/mcp`), or legacy SSE (`/sse`). A wrong transport or path fails at once.
3. **Opening the HTTP URL in a browser** shows an error such as "invalid request" — that is
   normal; MCP needs a client, not a browser GET.
4. **stdio specifics** — the server must write only JSON-RPC to stdout; logs go to stderr. A
   print statement or banner on stdout breaks the connection. Test the command alone in a
   terminal first.
5. **Windows** — some clients need `cmd /c npx ...` to start npm-based servers; paths with
   spaces need quoting; environment variables must be passed explicitly.
6. **Read the protocol view** — initialize, then tools/list, then tools/call: the first failing
   message and its error text point at the cause (timeouts, auth 401, schema validation).
7. **Authentication** — bearer tokens or OAuth for remote servers; the Inspector itself also
   uses a session token in its URL.

## Output shape
```
## MCP Connection Debug — orders-mcp
Symptom: card shows "Disconnected" after 30 s
Transport configured: streamable-http · URL http://localhost:8000/sse   ← mismatch
Server actually serves: Streamable HTTP at /mcp
Fix: change the URL to http://localhost:8000/mcp
Verified: initialize OK · tools/list returns 7 tools · get_order call OK
```

## Guardrails
- Do not paste Inspector session tokens or API keys into tickets or chats.
- Change one thing at a time and re-test, so the real cause is known.
- If the server runs elsewhere, check the port is reachable before debugging the protocol.
