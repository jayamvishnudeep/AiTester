"""Command line: tc-mcp [--transport stdio|http] [--host HOST] [--port PORT]."""

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tc-mcp", description="Test Creator MCP server for the VWO test case library.")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio",
                        help="stdio: one client starts the server (default). http: one server that many clients share.")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP only (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8932, help="HTTP only (default 8932)")
    args = parser.parse_args(argv)

    from .catalog import CatalogError

    try:
        from .server import mcp
    except CatalogError as error:
        sys.exit(f"tc-mcp: {error}")
    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
