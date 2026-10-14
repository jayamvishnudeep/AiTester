"""Entry point for the FastMCP CLI, which loads servers from a file:

    fastmcp dev inspector server.py
    fastmcp install claude-code server.py --name test-creator
"""

from test_creator_mcp.server import mcp

__all__ = ["mcp"]
