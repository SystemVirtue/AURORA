from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TABLES = [
    "workspaces", "workspace_members", "sources", "sessions", "events", "messages",
    "documents", "claims", "evidence", "entities", "relationships", "beliefs", "memories",
    "goals", "decisions", "reasoning_runs", "model_contributions", "epistemic_gaps",
]

# Tables with a direct workspace_id can be exported with one predicate. These two
# require joins through their parent aggregate to preserve tenant boundaries.
DIRECT_WORKSPACE_TABLES = [
    "sources", "sessions", "events", "messages", "documents", "claims", "evidence",
    "entities", "relationships", "beliefs", "memories", "goals", "decisions",
    "reasoning_runs", "epistemic_gaps",
]


def _stable_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Canonical ordering makes exports reproducible across machines/runs."""
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("id", "")),
            json.dumps(row, ensure_ascii=False, sort_keys=True, default=str),
        ),
    )


def export_json_bundle(rows_by_table: dict[str, list[dict[str, Any]]], destination: str | Path) -> Path:
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": "aurora-state",
        "version": 2,
        "exported_at": datetime.now(UTC).isoformat(),
        "authoritative_tables": TABLES,
        "derived_state": "rebuildable",
        "ordering": "stable id then canonical JSON",
    }
    checksums: dict[str, str] = {}
    for table in TABLES:
        path = root / f"{table}.json"
        payload = _stable_rows(rows_by_table.get(table, []))
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2).encode()
        path.write_bytes(raw)
        checksums[path.name] = hashlib.sha256(raw).hexdigest()
    manifest["checksums"] = checksums
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8"
    )
    return root


def verify_json_bundle(source: str | Path) -> dict[str, Any]:
    """Verify every exported table against the manifest before import."""
    root = Path(source)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "aurora-state":
        raise ValueError("not an AURORA state bundle")
    failures: list[str] = []
    for filename, expected in manifest.get("checksums", {}).items():
        path = root / filename
        if not path.exists():
            failures.append(f"missing:{filename}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            failures.append(f"checksum:{filename}")
    return {"valid": not failures, "failures": failures, "version": manifest.get("version")}


def export_workspace(conn: Any, workspace_id: str, destination: str | Path) -> Path:
    """Export authoritative workspace state; embeddings/indexes remain rebuildable."""
    rows: dict[str, list[dict[str, Any]]] = {}
    for table in DIRECT_WORKSPACE_TABLES:
        result = conn.execute(f"select * from public.{table} where workspace_id=%s", (workspace_id,))
        columns = [item.name for item in result.description]
        rows[table] = [dict(zip(columns, row)) for row in result.fetchall()]

    result = conn.execute("select * from public.workspaces where id=%s", (workspace_id,))
    columns = [item.name for item in result.description]
    rows["workspaces"] = [dict(zip(columns, row)) for row in result.fetchall()]

    result = conn.execute("select * from public.workspace_members where workspace_id=%s", (workspace_id,))
    columns = [item.name for item in result.description]
    rows["workspace_members"] = [dict(zip(columns, row)) for row in result.fetchall()]

    result = conn.execute(
        """select mc.* from public.model_contributions mc
           join public.reasoning_runs rr on rr.id=mc.reasoning_run_id
          where rr.workspace_id=%s""",
        (workspace_id,),
    )
    columns = [item.name for item in result.description]
    rows["model_contributions"] = [dict(zip(columns, row)) for row in result.fetchall()]
    return export_json_bundle(rows, destination)
