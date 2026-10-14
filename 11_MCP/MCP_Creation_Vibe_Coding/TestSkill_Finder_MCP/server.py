"""Entry point for the FastMCP CLI, which loads servers from a file:

    fastmcp dev inspector server.py
    fastmcp install claude-code server.py --name test-skill-finder
"""

from test_skill_finder_mcp.server import mcp

__all__ = ["mcp"]
