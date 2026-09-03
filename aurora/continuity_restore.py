from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aurora.continuity import TABLES, verify_json_bundle

# Parent-before-child ordering. Derived retrieval projections are deliberately excluded:
# they can be rebuilt from authoritative documents after restoration.
RESTORE_ORDER = [
    "workspaces",
    "workspace_members",
    "sources",
    "sessions",
    "events",
    "messages",
    "documents",
    "claims",
    "evidence",
    "entities",
    "relationships",
    "beliefs",
    "memories",
    "goals",
    "decisions",
    "reasoning_runs",
    "model_contributions",
    "epistemic_gaps",
]


def _read_table(root: Path, table: str) -> list[dict[str, Any]]:
    path = root / f"{table}.json"
    if not path.exists():
        raise ValueError(f"missing table file: {table}.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError(f"invalid table payload: {table}.json")
    return payload


def validate_restore_bundle(source: str | Path, workspace_id: str | None = None) -> dict[str, Any]:
    """Validate integrity, schema inventory, and optional workspace scope before restore."""
    root = Path(source)
    integrity = verify_json_bundle(root)
    failures = list(integrity["failures"])
    if not integrity["valid"]:
        return {"valid": False, "failures": failures, "rows": {}}

    rows: dict[str, int] = {}
    for table in RESTORE_ORDER:
        payload = _read_table(root, table)
        rows[table] = len(payload)
        if workspace_id and table not in {"workspaces", "workspace_members"}:
            for row in payload:
                if "workspace_id" in row and str(row["workspace_id"]) != str(workspace_id):
                    failures.append(f"workspace:{table}:{row.get('id', '<unknown>')}")
        if table == "workspaces" and workspace_id:
            ids = {str(row.get("id")) for row in payload}
            if str(workspace_id) not in ids:
                failures.append("workspace:missing")
        if table == "workspace_members" and workspace_id:
            for row in payload:
                if str(row.get("workspace_id")) != str(workspace_id):
                    failures.append(f"workspace:workspace_members:{row.get('user_id', '<unknown>')}")

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("authoritative_tables") != TABLES:
        failures.append("manifest:authoritative_tables")
    return {"valid": not failures, "failures": failures, "rows": rows, "order": RESTORE_ORDER}


def restore_workspace(conn: Any, source: str | Path, workspace_id: str, dry_run: bool = False) -> dict[str, Any]:
    """Restore a verified workspace using dependency-aware inserts.

    Existing rows with the same primary keys are rejected rather than silently merged.
    Embeddings/document_chunks are derived state and are intentionally rebuilt later.
    """
    validation = validate_restore_bundle(source, workspace_id)
    if not validation["valid"]:
        raise ValueError("restore validation failed: " + ", ".join(validation["failures"]))

    root = Path(source)
    rows_by_table = {table: _read_table(root, table) for table in RESTORE_ORDER}
    existing = conn.execute("select 1 from public.workspaces where id=%s", (workspace_id,)).fetchone()
    if existing:
        raise ValueError("workspace already exists")

    if dry_run:
        return {"restored": False, "dry_run": True, "rows": validation["rows"], "order": RESTORE_ORDER}

    inserted: dict[str, int] = {}
    try:
        for table in RESTORE_ORDER:
            rows = rows_by_table[table]
            if not rows:
                inserted[table] = 0
                continue
            columns = list(rows[0].keys())
            placeholders = ",".join(["%s"] * len(columns))
            quoted = ",".join(f'"{column}"' for column in columns)
            for row in rows:
                values = [row[column] for column in columns]
                conn.execute(
                    f"insert into public.{table} ({quoted}) values ({placeholders})",
                    values,
                )
            inserted[table] = len(rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return {"restored": True, "dry_run": False, "rows": inserted, "order": RESTORE_ORDER}
