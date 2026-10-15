# MCP

The [Model Context Protocol](https://modelcontextprotocol.io) (MCP) lets an AI client — Claude Code, Claude
Desktop, Cursor, VS Code, n8n, Langflow — call tools on a server. This folder has two MCP servers built here for
QA work, and the off-the-shelf servers in use alongside them.

## Built here

| Server | What it does | Connection string |
|---|---|---|
| [Test Creator MCP](MCP_Creation_Vibe_Coding/TestCase_Creator_MCP) | 20 tools over 5,000 VWO test cases: find cases by priority, module or keyword, rank the top tests to run for a module, build smoke and regression suites within limits, show coverage gaps and duplicates, and add new test cases in the house format | `http://127.0.0.1:8932/mcp` |
| [Test Skill Finder MCP](MCP_Creation_Vibe_Coding/TestSkill_Finder_MCP) | 100 QA skills — the STLC phases plus Playwright, Selenium, Cypress, API, mobile, performance, security, LLM evaluation, AI agents and MCP — found by keyword ("playwright api", "test case creator"), with 14 tools, resources and prompts. 36 of the skills come from [PramodDutta/skillmasterclass](https://github.com/PramodDutta/skillmasterclass) | `http://127.0.0.1:8933/mcp` |

Both are Python 3.10+ packages built with [FastMCP](https://gofastmcp.com) 4.1. They run over stdio (the client
starts them) or Streamable HTTP (the connection strings above, once started). Every tool's description ends with
a working example input, and each README walks through [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
with screenshots of real runs.

## Servers in use

Off-the-shelf servers, added to Claude Code with `npx` and shown as cards in MCP Inspector:

```bash
claude mcp add playwright npx @playwright/mcp@latest
claude mcp add selenium -- npx -y @angiejones/mcp-selenium@latest
claude mcp add github -- npx -y @modelcontextprotocol/server-github
claude mcp add jira -- npx -y mcp-remote https://mcp.atlassian.com/v1/mcp
claude mcp add slack -- npx -y slack-mcp-server@latest --transport stdio
claude mcp add figma -- npx -y figma-developer-mcp --stdio
```

| Server | Needs |
|---|---|
| Playwright | Nothing; it drives the installed Chrome |
| Selenium | A browser; Selenium Manager fetches the driver |
| GitHub | Optional `GITHUB_PERSONAL_ACCESS_TOKEN` (public data works without it) |
| Jira | An Atlassian login in the browser on first connect |
| Slack | `SLACK_MCP_XOXP_TOKEN` (or a bot token) |
| Figma | `FIGMA_API_KEY` |

Pass a token with `-e NAME=value` after the server name. [screenshots_MCP_Tools/](screenshots_MCP_Tools/) shows
them in MCP Inspector: [all the cards](screenshots_MCP_Tools/01-all-mcp-inspector-cards.png),
[Playwright](screenshots_MCP_Tools/02-playwright-mcp-inspector.png),
[Selenium](screenshots_MCP_Tools/03-selenium-mcp-inspector.png) and
[GitHub](screenshots_MCP_Tools/04-github-mcp-inspector.png).
