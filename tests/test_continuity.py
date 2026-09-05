import json

from aurora.continuity import TABLES, export_json_bundle, verify_json_bundle


def test_export_writes_manifest_and_checksums(tmp_path):
    root = export_json_bundle({"events": [{"id": "1", "event_type": "test"}]}, tmp_path / "export")
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["format"] == "aurora-state"
    assert manifest["version"] == 3
    assert manifest["authoritative_tables"] == TABLES
    assert "tasks" in manifest["authoritative_tables"]
    assert "events.json" in manifest["checksums"]
    assert "tasks.json" in manifest["checksums"]
    assert (root / "events.json").exists()
    assert verify_json_bundle(root)["valid"] is True


def test_export_order_is_stable(tmp_path):
    a = {"events": [{"id": "2", "x": 2}, {"id": "1", "x": 1}]}
    b = {"events": [{"id": "1", "x": 1}, {"id": "2", "x": 2}]}
    export_json_bundle(a, tmp_path / "a")
    export_json_bundle(b, tmp_path / "b")
    assert (tmp_path / "a" / "events.json").read_bytes() == (tmp_path / "b" / "events.json").read_bytes()


def test_verify_detects_tampering(tmp_path):
    root = export_json_bundle({"events": [{"id": "1", "event_type": "test"}]}, tmp_path / "export")
    (root / "events.json").write_text("[]", encoding="utf-8")
    result = verify_json_bundle(root)
    assert result["valid"] is False
    assert "checksum:events.json" in result["failures"]
