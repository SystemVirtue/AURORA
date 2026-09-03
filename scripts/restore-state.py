"""Restore an AURORA workspace bundle into a fresh PostgreSQL/Supabase database."""
from __future__ import annotations

import argparse
import json
import os

import psycopg

from aurora.continuity_restore import restore_workspace, validate_restore_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="AURORA state bundle directory")
    parser.add_argument("workspace_id", help="workspace UUID contained in the bundle")
    parser.add_argument("--user-map", default="{}", help="JSON mapping of old auth user UUIDs to new UUIDs")
    parser.add_argument("--dry-run", action="store_true", help="validate only; do not write")
    args = parser.parse_args()

    mapping = json.loads(args.user_map)
    if not isinstance(mapping, dict):
        raise SystemExit("--user-map must be a JSON object")

    validation = validate_restore_bundle(args.bundle, args.workspace_id, mapping)
    print(json.dumps(validation, indent=2, default=str))
    if not validation["valid"]:
        return 2
    if args.dry_run:
        return 0

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    with psycopg.connect(database_url) as conn:
        result = restore_workspace(conn, args.bundle, args.workspace_id, user_id_map=mapping)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
