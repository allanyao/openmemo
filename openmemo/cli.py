"""
OpenMemo CLI - Command line interface.

Usage:
    openmemo serve [--port PORT] [--db DB_PATH]
    openmemo mcp serve [--transport stdio|sse] [--port PORT] [--db DB_PATH]
    openmemo version
    openmemo check-update
    openmemo upgrade
    openmemo migrate [--db DB_PATH]
    openmemo inspector [--port PORT]
    openmemo checklist [--port PORT]
    openmemo memory [--port PORT]
    openmemo search <query> [--port PORT]
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="openmemo",
        description="OpenMemo - The Memory Infrastructure for AI Agents",
    )
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the OpenMemo API server")
    serve_parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    serve_parser.add_argument("--host", type=str, default="127.0.0.1")
    serve_parser.add_argument("--db", type=str, default=os.environ.get("OPENMEMO_DB", "openmemo.db"))

    subparsers.add_parser("version", help="Show installed version info")

    subparsers.add_parser("check-update", help="Check for available updates")

    subparsers.add_parser("upgrade", help="Upgrade openmemo and openmemo-openclaw to latest")

    migrate_parser = subparsers.add_parser("migrate", help="Run schema migrations")
    migrate_parser.add_argument(
        "--db", type=str, default=os.environ.get("OPENMEMO_DB", "openmemo.db"),
        help="Path to the SQLite database",
    )

    inspector_parser = subparsers.add_parser("inspector", help="Open Memory Inspector in browser")
    inspector_parser.add_argument("--port", type=int, default=8765)

    checklist_parser = subparsers.add_parser("checklist", help="Show memory system checklist")
    checklist_parser.add_argument("--port", type=int, default=8765)

    memory_parser = subparsers.add_parser("memory", help="Show memory summary")
    memory_parser.add_argument("--port", type=int, default=8765)

    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument("--port", type=int, default=8765)

    mcp_parser = subparsers.add_parser("mcp", help="MCP server commands")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_command")
    mcp_serve = mcp_sub.add_parser("serve", help="Start MCP server")
    mcp_serve.add_argument(
        "--transport", choices=["stdio", "sse", "http"], default="stdio",
        help="Transport mode: stdio (default), sse (legacy), http (streamable HTTP for claude.ai)",
    )
    mcp_serve.add_argument("--host", default="127.0.0.1", help="SSE host (SSE mode only)")
    mcp_serve.add_argument("--port", type=int, default=8780, help="SSE port (SSE mode only)")
    mcp_serve.add_argument(
        "--db", type=str, default=os.environ.get("OPENMEMO_DB", "openmemo.db"),
        help="Database path",
    )
    mcp_serve.add_argument("--agent-id", default="", help="Agent identifier")

    args = parser.parse_args()

    if args.command == "serve":
        _cmd_serve(args)
    elif args.command == "version":
        _cmd_version()
    elif args.command == "check-update":
        _cmd_check_update()
    elif args.command == "upgrade":
        _cmd_upgrade()
    elif args.command == "migrate":
        _cmd_migrate(args)
    elif args.command == "inspector":
        _cmd_inspector(args)
    elif args.command == "checklist":
        _cmd_checklist(args)
    elif args.command == "memory":
        _cmd_memory(args)
    elif args.command == "search":
        _cmd_search(args)
    elif args.command == "mcp":
        _cmd_mcp(args)
    else:
        parser.print_help()


def _cmd_serve(args):
    try:
        from openmemo.api.rest_server import create_app
    except ImportError:
        print("Server dependencies not installed. Run: pip install openmemo[server]")
        sys.exit(1)

    app = create_app(db_path=args.db)
    print(f"OpenMemo API Server starting on {args.host}:{args.port}")
    print(f"Database: {args.db}")
    print(f"Docs: http://{args.host}:{args.port}/docs")
    print(f"Inspector: http://{args.host}:{args.port}/inspector")
    app.run(host=args.host, port=args.port)


def _cmd_version():
    from openmemo.upgrade import get_local_versions

    versions = get_local_versions()
    print("OpenMemo Version Info")
    print(f"  Core:           {versions['core'] or 'not installed'}")
    print(f"  Adapter:        {versions['adapter'] or 'not installed'}")
    print(f"  Schema Version: {versions['schema_version']}")


def _cmd_check_update():
    from openmemo.upgrade import version_check

    print("Checking for updates...")
    result = version_check()
    local = result["local"]
    remote = result["remote"]

    print(f"\nLocal versions:")
    print(f"  Core:    {local['core'] or 'not installed'}")
    print(f"  Adapter: {local['adapter'] or 'not installed'}")

    if remote:
        print(f"\nLatest versions:")
        print(f"  Core:    {remote.get('latest_core', 'unknown')}")
        print(f"  Adapter: {remote.get('latest_adapter', 'unknown')}")

        if result["update_available"]:
            print("\nUpdates available! Run: openmemo upgrade")
        else:
            print("\nYou are up to date.")
    else:
        print("\nCould not reach api.openmemo.ai to check for updates.")


def _cmd_upgrade():
    from openmemo.upgrade import run_upgrade

    print("Upgrading openmemo and openmemo-openclaw...")
    result = run_upgrade()
    if result.returncode == 0:
        print("Upgrade complete.")
    else:
        print("Upgrade failed. Check pip output above.")
        sys.exit(1)


def _cmd_migrate(args):
    try:
        from openmemo.migration import SchemaMigrator
    except ImportError:
        print("Migration module not available.")
        sys.exit(1)

    migrator = SchemaMigrator(args.db)
    current = migrator.get_schema_version()
    print(f"Current schema version: {current}")
    migrator.run_migrations()
    new_version = migrator.get_schema_version()
    if new_version > current:
        print(f"Migrated to schema version {new_version}")
    else:
        print("Schema is already up to date.")


def _cmd_inspector(args):
    import webbrowser
    url = f"http://localhost:{args.port}/inspector"
    print(f"Opening Memory Inspector: {url}")
    webbrowser.open(url)


def _cmd_checklist(args):
    data = _api_get(args.port, "/api/inspector/checklist")
    if not data:
        print("Could not connect to OpenMemo server. Is it running?")
        sys.exit(1)

    print("Memory System Checklist")
    print("-" * 40)
    for check in data.get("checks", []):
        status = check["status"]
        icon = {"ok": "[OK]", "warning": "[!!]", "fail": "[FAIL]", "cold_start": "[COLD]"}.get(status, "[??]")
        print(f"  {icon} {check['name']}")


def _cmd_memory(args):
    data = _api_get(args.port, "/api/inspector/memory-summary")
    if not data:
        print("Could not connect to OpenMemo server. Is it running?")
        sys.exit(1)

    print("Memory Summary")
    print("-" * 40)
    print(f"  Total Memories: {data.get('total_memories', 0)}")
    print(f"  Total Cells:    {data.get('total_cells', 0)}")
    print(f"  Scenes:         {data.get('total_scenes', 0)}")

    type_dist = data.get("type_distribution", {})
    if type_dist:
        print("\n  Type Distribution:")
        for k, v in type_dist.items():
            print(f"    {k}: {v}")

    scene_dist = data.get("scene_distribution", {})
    if scene_dist:
        print("\n  Scene Distribution:")
        for k, v in scene_dist.items():
            print(f"    {k or '(none)'}: {v}")


def _cmd_search(args):
    import urllib.parse
    q = urllib.parse.quote(args.query)
    data = _api_get(args.port, f"/api/inspector/search?q={q}")
    if not data:
        print("Could not connect to OpenMemo server. Is it running?")
        sys.exit(1)

    results = data.get("results", [])
    if not results:
        print(f"No results for '{args.query}'")
        return

    print(f"Search results for '{args.query}' ({len(results)} found)")
    print("-" * 40)
    for i, r in enumerate(results, 1):
        content = r.get("content", r.get("text", ""))[:100]
        scene = r.get("scene", "")
        score = r.get("score", "")
        print(f"  {i}. {content}")
        meta = []
        if scene:
            meta.append(f"scene={scene}")
        if score:
            meta.append(f"score={score:.2f}" if isinstance(score, float) else f"score={score}")
        if meta:
            print(f"     [{', '.join(meta)}]")


def _cmd_mcp(args):
    if not hasattr(args, "mcp_command") or args.mcp_command != "serve":
        print("Usage: openmemo mcp serve [--transport stdio|sse] [--port PORT] [--db DB_PATH]")
        return

    from openmemo.adapters.mcp_server import run_stdio, run_sse, run_http

    if args.transport == "sse":
        run_sse(
            host=args.host,
            port=args.port,
            db_path=args.db,
            agent_id=getattr(args, "agent_id", ""),
        )
    elif args.transport == "http":
        run_http(
            host=args.host,
            port=args.port,
            db_path=args.db,
            agent_id=getattr(args, "agent_id", ""),
        )
    else:
        run_stdio(
            db_path=args.db,
            agent_id=getattr(args, "agent_id", ""),
        )


def _api_get(port, path):
    try:
        import urllib.request
        import json
        url = f"http://localhost:{port}{path}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


if __name__ == "__main__":
    main()
