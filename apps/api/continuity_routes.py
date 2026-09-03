from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aurora.continuity import TABLES, export_workspace
from aurora.continuity_restore import restore_workspace, validate_restore_bundle
from aurora.core import settings

router = APIRouter(prefix="/v1/continuity", tags=["continuity"])


class ContinuityRestoreRequest(BaseModel):
    workspace_id: uuid.UUID
    user_id_map: dict[str, uuid.UUID] = Field(default_factory=dict)
    bundle: dict[str, object]
    dry_run: bool = False


def _authenticated_user(credentials):
    from apps.api.main import current_user
    return current_user(credentials)


def _workspace_access(conn, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if not conn.execute(
        "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
        (workspace_id, user_id),
    ).fetchone():
        raise HTTPException(403, "User is not a member of this workspace")


def _write_bundle(root: Path, bundle: dict[str, object]) -> None:
    manifest = bundle.get("manifest")
    if not isinstance(manifest, dict):
        raise HTTPException(422, "bundle.manifest is required")
    (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8")
    for table in TABLES:
        payload = bundle.get(table)
        if not isinstance(payload, list):
            raise HTTPException(422, f"bundle.{table} must be a list")
        (root / f"{table}.json").write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


@router.get("/export")
def export_continuity(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID = Depends(_authenticated_user),  # noqa: B008
) -> dict:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    with tempfile.TemporaryDirectory(prefix="aurora-export-") as tmp:
        with psycopg.connect(settings.database_url) as conn:
            _workspace_access(conn, workspace_id, user_id)
            export_workspace(conn, str(workspace_id), tmp)
        root = Path(tmp)
        files = {"manifest": json.loads((root / "manifest.json").read_text(encoding="utf-8"))}
        for table in TABLES:
            files[table] = json.loads((root / f"{table}.json").read_text(encoding="utf-8"))
    return {"workspace_id": str(workspace_id), "format": "aurora-state", "bundle": files}


@router.post("/restore")
def restore_continuity(
    request: ContinuityRestoreRequest,
    user_id: uuid.UUID = Depends(_authenticated_user),  # noqa: B008
) -> dict:
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    # The caller must already control the target workspace namespace. For a real restore
    # into a fresh workspace, the mapped user must be a member of the bundle workspace.
    if user_id not in request.user_id_map.values() and str(user_id) not in request.user_id_map:
        raise HTTPException(403, "Authenticated user must be present in user_id_map")
    with tempfile.TemporaryDirectory(prefix="aurora-restore-") as tmp:
        root = Path(tmp)
        _write_bundle(root, request.bundle)
        mapping = {str(k): str(v) for k, v in request.user_id_map.items()}
        with psycopg.connect(settings.database_url) as conn:
            for target in mapping.values():
                if not conn.execute("select 1 from auth.users where id=%s", (target,)).fetchone():
                    raise HTTPException(422, f"mapped auth user does not exist: {target}")
            validation = validate_restore_bundle(root, str(request.workspace_id), mapping)
            if not validation["valid"]:
                raise HTTPException(422, {"restore_validation": validation})
            try:
                result = restore_workspace(
                    conn, root, str(request.workspace_id), dry_run=request.dry_run, user_id_map=mapping,
                )
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
    return {"workspace_id": str(request.workspace_id), **result}
