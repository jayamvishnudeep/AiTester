---
name: mcp-client-config-helper
description: >-
  Connects MCP servers to clients: Claude Code, Claude Desktop, Cursor, VS Code and MCP
  Inspector. Use when someone says "add this MCP server to Claude Code", "what's the config for
  Cursor or VS Code", "connect to a remote MCP URL", or "the server is configured but no tools
  appear". Produces the right command or JSON for each client (stdio command or HTTP URL),
  scope choices, environment variables for secrets, Windows notes, and how to verify the
  connection.
license: MIT
metadata:
  author: AiTester
  pack: mcp
  version: 1.0.0
---

# MCP Client Config Helper

You give **the exact configuration for the client in use** — command or URL, scope, secrets —
and a way to prove it connected.

## When to use
- A server works (for example in MCP Inspector) and now needs to be added to a client.
- A config exists but the tools do not appear.

## Workflow
1. **Identify the server** — stdio (a command such as `npx -y <package>` or a Python entry point)
   or remote (a Streamable HTTP URL ending in `/mcp`), plus required environment variables.
2. **Write the client config:**
   - Claude Code: `claude mcp add <name> -- <command> [args]`, or
     `claude mcp add --transport http <name> <url>`; scope with `-s local|project|user`
     (project scope writes `.mcp.json` for the team).
   - Claude Desktop: `claude_desktop_config.json` → `"mcpServers": {"<name>": {"command": ..., "args": [...]}}`.
   - Cursor: `.cursor/mcp.json` with the same `mcpServers` shape.
   - VS Code: `.vscode/mcp.json` → `"servers": {"<name>": {"type": "stdio" | "http", ...}}`.
   - MCP Inspector: a server entry with the transport and command or URL.
3. **Secrets** — environment variables (`-e KEY=value`, or `env` in JSON) filled from a secret
   store; never commit them in project config files.
4. **Windows** — some clients need `cmd /c npx ...` for npm-based servers; quote paths with spaces.
5. **Verify** — `claude mcp list` or the client's MCP panel shows it connected; list the tools;
   restart or open a new session if the client loads servers only at start-up.

## Output shape
```bash
# Claude Code, this project only
claude mcp add test-skill-finder -- "<path>\.venv\Scripts\tsf-mcp.exe"
# Claude Code, a shared HTTP server
claude mcp add --transport http test-skill-finder http://127.0.0.1:8933/mcp
```
```json
{
  "mcpServers": {
    "test-skill-finder": { "command": "<path>/.venv/Scripts/tsf-mcp.exe" }
  }
}
```

## Guardrails
- Never commit tokens in `.mcp.json`, `mcp.json` or client settings files.
- Use project scope only for servers the whole team should get; personal servers stay local.
- Check the client's documentation for its current config format; formats evolve.
