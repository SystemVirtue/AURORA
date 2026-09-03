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


def export_json_bundle(rows_by_table: dict[str, list[dict[str, Any]]], destination: str | Path) -> Path:
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": "aurora-state",
        "version": 1,
        "exported_at": datetime.now(UTC).isoformat(),
        "authoritative_tables": TABLES,
        "derived_state": "rebuildable",
    }
    checksums: dict[str, str] = {}
    for table in TABLES:
        path = root / f"{table}.json"
        payload = rows_by_table.get(table, [])
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2).encode()
        path.write_bytes(raw)
        checksums[path.name] = hashlib.sha256(raw).hexdigest()
    manifest["checksums"] = checksums
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return root
