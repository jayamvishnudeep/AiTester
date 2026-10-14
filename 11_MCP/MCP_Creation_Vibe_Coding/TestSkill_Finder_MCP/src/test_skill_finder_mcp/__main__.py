"""Command line.

  tsf-mcp                              serve over stdio (for a client that starts the server)
  tsf-mcp --transport http --port 8933 serve over HTTP at http://127.0.0.1:8933/mcp
  tsf-mcp sync [--apply] [--force]     pull the upstream skills (dry run unless --apply)
  tsf-mcp validate                     check every skill against the house format
  tsf-mcp catalog                      print the catalog as a Markdown table
"""

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="tsf-mcp", description="Test Skill Finder MCP server.")
    parser.add_argument("command", nargs="?", default="serve", choices=("serve", "sync", "validate", "catalog"))
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8933)
    parser.add_argument("--apply", action="store_true", help="sync: write the changes")
    parser.add_argument("--force", action="store_true", help="sync: overwrite upstream files edited locally")
    args = parser.parse_args(argv)

    from .catalog import CatalogError, load_catalog
    from .settings import load_settings

    settings = load_settings()
    if args.command == "sync":
        from .sync import sync

        report = sync(settings, apply=args.apply, force=args.force)
        print(f"{report.repository}@{report.branch} commit {report.commit[:12]}")
        for label in ("added", "updated", "removed", "conflicts"):
            for item in getattr(report, label):
                print(f"  {label:<9} {item}")
        print(f"  unchanged {report.unchanged}")
        print("\n".join(report.notes))
        return
    try:
        catalog = load_catalog(settings.skills_dir)
    except CatalogError as error:
        sys.exit(f"tsf-mcp: {error}")
    if args.command == "validate":
        from .authoring import validate

        report = validate(catalog)
        print(f"{report.valid}/{report.total} skills valid")
        for problem in report.problems:
            print(f"  {problem.skill}: {problem.problem}")
        sys.exit(1 if report.problems else 0)
    if args.command == "catalog":
        print("| # | Skill | Category | Source | What it does |")
        print("|---|---|---|---|---|")
        for n, skill in enumerate(catalog.skills, 1):
            print(f"| {n} | `{skill.name}` | {skill.category} | {skill.source} | {skill.summary.replace('|', '/')} |")
        return

    from .server import mcp

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
