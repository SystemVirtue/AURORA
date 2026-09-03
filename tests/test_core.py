from aurora.core import event_envelope


def test_event_envelope_is_traceable():
    event = event_envelope(
        event_type="test.created",
        producer_type="system",
        workspace_id="00000000-0000-0000-0000-000000000001",
        correlation_id="00000000-0000-0000-0000-000000000002",
        payload={"ok": True},
    )
    assert event["event_type"] == "test.created"
    assert event["producer_type"] == "system"
    assert event["schema_version"] == 1
    assert event["payload"] == {"ok": True}
    assert event["correlation_id"]


def test_event_id_is_unique():
    a = event_envelope(event_type="a", producer_type="system", workspace_id="w", payload={})
    b = event_envelope(event_type="a", producer_type="system", workspace_id="w", payload={})
    assert a["id"] != b["id"]
