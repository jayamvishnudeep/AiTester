# MCP pack

A domain pack: 6 skills that plug into the STLC phases. Each folder holds a `SKILL.md`: a short header plus the instructions an AI assistant follows.

| Skill | What it does | From |
|---|---|---|
| [mcp-client-config-helper](mcp-client-config-helper/SKILL.md) | Connects MCP servers to clients: Claude Code, Claude Desktop, Cursor, VS Code and MCP Inspector. | added here |
| [mcp-inspector-debugger](mcp-inspector-debugger/SKILL.md) | Debugs MCP server connections and calls with MCP Inspector. | added here |
| [mcp-security-reviewer](mcp-security-reviewer/SKILL.md) | Reviews the security of MCP servers and of the MCP servers a team plans to install. | added here |
| [mcp-server-builder](mcp-server-builder/SKILL.md) | Scaffolds a Model Context Protocol (MCP) server with tools, resources and prompts, ready to test. | added here |
| [mcp-server-tester](mcp-server-tester/SKILL.md) | Tests an MCP server's tools, resources and prompts through the protocol, the way a client sees them. | added here |
| [mcp-tool-design-reviewer](mcp-tool-design-reviewer/SKILL.md) | Reviews MCP tool design for how well LLMs can use the tools. | added here |

Search them by keyword with the [Test Skill Finder MCP](../../../README.md), or install one in Claude Code by copying
its folder to `~/.claude/skills/`.
