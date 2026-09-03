from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aurora.cognition import chunk_text, content_hash
from aurora.continuity import TABLES, verify_json_bundle

RESTORE_ORDER = [
    "workspaces", "workspace_members", "sources", "sessions", "events", "messages",
    "documents", "claims", "evidence", "entities", "relationships", "beliefs", "memories",
    "goals", "decisions", "reasoning_runs", "model_contributions", "epistemic_gaps",
]

AUTH_USER_FIELDS = {
    "workspaces": ("created_by",),
    "workspace_members": ("user_id",),
    "sessions": ("user_id",),
    "events": ("producer_id",),
}


def _read_table(root: Path, table: str) -> list[dict[str, Any]]:
    path = root / f"{table}.json"
    if not path.exists():
        raise ValueError(f"missing table file: {table}.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError(f"invalid table payload: {table}.json")
    return payload


def _map_user(value: Any, user_id_map: dict[str, str]) -> Any:
    return None if value is None else user_id_map.get(str(value), value)


def _mapped_row(table: str, row: dict[str, Any], user_id_map: dict[str, str]) -> dict[str, Any]:
    result = dict(row)
    for field in AUTH_USER_FIELDS.get(table, ()):
        if field in result:
            result[field] = _map_user(result[field], user_id_map)
    return result


def validate_restore_bundle(
    source: str | Path,
    workspace_id: str | None = None,
    user_id_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Validate integrity, schema inventory, tenant scope, and auth dependencies."""
    root = Path(source)
    integrity = verify_json_bundle(root)
    failures = list(integrity["failures"])
    if not integrity["valid"]:
        return {"valid": False, "failures": failures, "rows": {}}

    user_id_map = user_id_map or {}
    rows: dict[str, int] = {}
    for table in RESTORE_ORDER:
        payload = _read_table(root, table)
        rows[table] = len(payload)
        if workspace_id and table not in {"workspaces", "workspace_members"}:
            for row in payload:
                if "workspace_id" in row and str(row["workspace_id"]) != str(workspace_id):
                    failures.append(f"workspace:{table}:{row.get('id', '<unknown>')}")
        if table == "workspaces" and workspace_id and str(workspace_id) not in {
            str(row.get("id")) for row in payload
        }:
            failures.append("workspace:missing")
        if table == "workspace_members" and workspace_id:
            for row in payload:
                if str(row.get("workspace_id")) != str(workspace_id):
                    failures.append(f"workspace:workspace_members:{row.get('user_id', '<unknown>')}")
        for field in AUTH_USER_FIELDS.get(table, ()):
            for row in payload:
                value = row.get(field)
                if value is not None and str(value) not in user_id_map:
                    failures.append(f"auth_dependency:{table}:{field}:{value}")

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("authoritative_tables") != TABLES:
        failures.append("manifest:authoritative_tables")
    return {"valid": not failures, "failures": failures, "rows": rows, "order": RESTORE_ORDER}


def restore_workspace(
    conn: Any,
    source: str | Path,
    workspace_id: str,
    dry_run: bool = False,
    user_id_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Restore verified state with dependency-aware inserts and explicit auth remapping."""
    user_id_map = user_id_map or {}
    validation = validate_restore_bundle(source, workspace_id, user_id_map)
    if not validation["valid"]:
        raise ValueError("restore validation failed: " + ", ".join(validation["failures"]))

    root = Path(source)
    rows_by_table = {
        table: [_mapped_row(table, row, user_id_map) for row in _read_table(root, table)]
        for table in RESTORE_ORDER
    }
    if conn.execute("select 1 from public.workspaces where id=%s", (workspace_id,)).fetchone():
        raise ValueError("workspace already exists")
    if dry_run:
        return {"restored": False, "dry_run": True, "rows": validation["rows"], "order": RESTORE_ORDER}

    inserted: dict[str, int] = {}
    try:
        for table in RESTORE_ORDER:
            rows = rows_by_table[table]
            inserted[table] = 0
            if not rows:
                continue
            columns = list(rows[0].keys())
            placeholders = ",".join(["%s"] * len(columns))
            quoted = ",".join(f'"{column}"' for column in columns)
            for row in rows:
                conn.execute(
                    f"insert into public.{table} ({quoted}) values ({placeholders})",
                    [row[column] for column in columns],
                )
            inserted[table] = len(rows)
        rebuilt = rebuild_document_chunks(conn, workspace_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {
        "restored": True,
        "dry_run": False,
        "rows": inserted,
        "rebuilt": {"document_chunks": rebuilt},
        "order": RESTORE_ORDER,
    }


def rebuild_document_chunks(conn: Any, workspace_id: str) -> int:
    """Recreate the derived chunk projection deterministically from authoritative documents."""
    conn.execute("delete from public.document_chunks where workspace_id=%s", (workspace_id,))
    documents = conn.execute(
        "select id, content from public.documents where workspace_id=%s order by id", (workspace_id,)
    ).fetchall()
    rebuilt = 0
    for document_id, content in documents:
        for index, chunk in enumerate(chunk_text(content or "")):
            conn.execute(
                """insert into public.document_chunks
                   (workspace_id,document_id,chunk_index,content,content_hash,token_estimate)
                   values (%s,%s,%s,%s,%s,%s)""",
                (workspace_id, document_id, index, chunk, content_hash(chunk), max(1, len(chunk) // 4)),
            )
            rebuilt += 1
    return rebuilt
