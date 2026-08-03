def test_audit_log_lists_full_lifecycle_in_order(client) -> None:
    create_response = client.post("/action-points", json={"transcript": "schedule a meeting", "confidence": 0.9})
    action_point_id = create_response.json()["id"]
    client.post(f"/action-points/{action_point_id}/approve", json={"approver": "alice"})
    client.post(f"/action-points/{action_point_id}/execute")

    response = client.get(f"/audit-log?action_point_id={action_point_id}")

    assert response.status_code == 200
    event_types = [entry["event_type"] for entry in response.json()]
    assert event_types == ["PROPOSED", "APPROVED", "EXECUTED"]


def test_audit_log_without_filter_returns_all_events(client) -> None:
    client.post("/action-points", json={"transcript": "schedule a meeting", "confidence": 0.9})

    response = client.get("/audit-log")

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_audit_log_records_rejection(client) -> None:
    create_response = client.post("/action-points", json={"transcript": "schedule a meeting", "confidence": 0.9})
    action_point_id = create_response.json()["id"]
    client.post(f"/action-points/{action_point_id}/reject", json={"approver": "bob", "reason": "no longer needed"})

    response = client.get(f"/audit-log?action_point_id={action_point_id}")

    event_types = [entry["event_type"] for entry in response.json()]
    assert event_types == ["PROPOSED", "REJECTED"]
