import json

from aurora.continuity import export_json_bundle


def test_export_writes_manifest_and_checksums(tmp_path):
    root = export_json_bundle({"events": [{"id": "1", "event_type": "test"}]}, tmp_path / "export")
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["format"] == "aurora-state"
    assert manifest["version"] == 1
    assert "events.json" in manifest["checksums"]
    assert (root / "events.json").exists()
