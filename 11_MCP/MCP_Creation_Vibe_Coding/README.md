# MCP Creation (Vibe Coding)

The two MCP servers built in this repository, each a Python package with its own `.venv`, tests and README.

| Server | What it does | Command | Connection string |
|---|---|---|---|
| [TestCase_Creator_MCP](TestCase_Creator_MCP) | Test Creator: 20 tools over 5,000 VWO test cases — find by priority, module or keyword, the top tests to run, smoke and regression suites, coverage gaps, duplicates, new test cases in the house format | `tc-mcp` | `http://127.0.0.1:8932/mcp` |
| [TestSkill_Finder_MCP](TestSkill_Finder_MCP) | Test Skill Finder: 100 QA skills found by keyword, with 14 tools, 4 resources and 4 prompts | `tsf-mcp` | `http://127.0.0.1:8933/mcp` |

Both are built with [FastMCP](https://gofastmcp.com) 4.1 and need Python 3.10 or later. To try one:

```powershell
cd TestSkill_Finder_MCP          # or TestCase_Creator_MCP
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\tsf-mcp --transport http --port 8933    # tc-mcp --transport http --port 8932 for Test Creator
```

Then connect MCP Inspector or any MCP client to the connection string. Without `--transport http` the server
speaks stdio, for clients that start it themselves (Claude Code, Claude Desktop, Cursor).

The Test Creator design is in [TestCase_Creator_MCP/TestCreatorMCP.plan.md](TestCase_Creator_MCP/TestCreatorMCP.plan.md),
and the goal it started from is in [TestCase_Creator_MCP/objective.md](TestCase_Creator_MCP/objective.md).
