import json

import pytest

from aurora.continuity import export_json_bundle
from aurora.continuity_restore import RESTORE_ORDER, validate_restore_bundle


def test_restore_validation_accepts_verified_workspace_bundle(tmp_path):
    rows = {table: [] for table in RESTORE_ORDER}
    rows["workspaces"] = [{"id": "w1", "name": "Test", "slug": "test", "created_by": "u1"}]
    rows["workspace_members"] = [{"workspace_id": "w1", "user_id": "u1", "role": "owner"}]
    rows["sources"] = [{"id": "s1", "workspace_id": "w1"}]
    root = export_json_bundle(rows, tmp_path / "bundle")
    result = validate_restore_bundle(root, "w1")
    assert result["valid"] is True
    assert result["rows"]["sources"] == 1
    assert result["order"] == RESTORE_ORDER


def test_restore_validation_rejects_cross_workspace_rows(tmp_path):
    rows = {table: [] for table in RESTORE_ORDER}
    rows["workspaces"] = [{"id": "w1"}]
    rows["workspace_members"] = [{"workspace_id": "w1", "user_id": "u1"}]
    rows["sources"] = [{"id": "s1", "workspace_id": "w2"}]
    root = export_json_bundle(rows, tmp_path / "bundle")
    result = validate_restore_bundle(root, "w1")
    assert result["valid"] is False
    assert any(item.startswith("workspace:sources:") for item in result["failures"])


def test_restore_validation_rejects_tampered_bundle(tmp_path):
    rows = {table: [] for table in RESTORE_ORDER}
    rows["workspaces"] = [{"id": "w1"}]
    rows["workspace_members"] = [{"workspace_id": "w1", "user_id": "u1"}]
    root = export_json_bundle(rows, tmp_path / "bundle")
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["checksums"]["workspaces.json"] = "0" * 64
    (root / "manifest.json").write_text(json.dumps(manifest))
    result = validate_restore_bundle(root, "w1")
    assert result["valid"] is False
    assert "checksum:workspaces.json" in result["failures"]


def test_restore_order_places_dependencies_before_dependants():
    assert RESTORE_ORDER.index("workspaces") < RESTORE_ORDER.index("documents")
    assert RESTORE_ORDER.index("documents") < RESTORE_ORDER.index("claims")
    assert RESTORE_ORDER.index("claims") < RESTORE_ORDER.index("evidence")
    assert RESTORE_ORDER.index("reasoning_runs") < RESTORE_ORDER.index("model_contributions")
