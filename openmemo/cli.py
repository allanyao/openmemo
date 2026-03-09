"""
OpenMemo CLI - Command line interface.

Usage:
    openmemo serve [--port PORT] [--db DB_PATH]
    openmemo version
    openmemo check-update
    openmemo upgrade
    openmemo migrate [--db DB_PATH]
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
    serve_parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))
    serve_parser.add_argument("--host", type=str, default="0.0.0.0")
    serve_parser.add_argument("--db", type=str, default=os.environ.get("OPENMEMO_DB", "openmemo.db"))

    subparsers.add_parser("version", help="Show installed version info")

    subparsers.add_parser("check-update", help="Check for available updates")

    subparsers.add_parser("upgrade", help="Upgrade openmemo and openmemo-openclaw to latest")

    migrate_parser = subparsers.add_parser("migrate", help="Run schema migrations")
    migrate_parser.add_argument(
        "--db", type=str, default=os.environ.get("OPENMEMO_DB", "openmemo.db"),
        help="Path to the SQLite database",
    )

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
            print("\n✨ Updates available! Run: openmemo upgrade")
        else:
            print("\n✅ You are up to date.")
    else:
        print("\n⚠️  Could not reach api.openmemo.ai to check for updates.")


def _cmd_upgrade():
    from openmemo.upgrade import run_upgrade

    print("Upgrading openmemo and openmemo-openclaw...")
    result = run_upgrade()
    if result.returncode == 0:
        print("✅ Upgrade complete.")
    else:
        print("❌ Upgrade failed. Check pip output above.")
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
        print(f"✅ Migrated to schema version {new_version}")
    else:
        print("✅ Schema is already up to date.")


if __name__ == "__main__":
    main()
