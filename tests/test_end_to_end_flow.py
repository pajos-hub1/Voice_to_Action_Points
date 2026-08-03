def test_happy_path_transcribe_to_audit(client) -> None:
    transcribe_response = client.post(
        "/transcribe",
        files={"file": ("sample.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert transcribe_response.status_code == 200
    transcript_body = transcribe_response.json()

    create_response = client.post(
        "/action-points",
        json={"transcript": transcript_body["text"], "confidence": transcript_body["confidence"]},
    )
    assert create_response.status_code == 201
    action_point_id = create_response.json()["id"]
    assert create_response.json()["status"] == "PENDING_APPROVAL"

    approve_response = client.post(f"/action-points/{action_point_id}/approve", json={"approver": "alice"})
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"

    execute_response = client.post(f"/action-points/{action_point_id}/execute")
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == "EXECUTED"
    assert execute_response.json()["execution_result"] is not None

    audit_response = client.get(f"/audit-log?action_point_id={action_point_id}")
    event_types = [entry["event_type"] for entry in audit_response.json()]
    assert event_types == ["PROPOSED", "APPROVED", "EXECUTED"]


def test_rejected_path_never_executes(client) -> None:
    create_response = client.post(
        "/action-points",
        json={"transcript": "delete the staging database", "confidence": 0.9},
    )
    action_point_id = create_response.json()["id"]

    reject_response = client.post(
        f"/action-points/{action_point_id}/reject",
        json={"approver": "bob", "reason": "too risky"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "REJECTED"

    execute_response = client.post(f"/action-points/{action_point_id}/execute")
    assert execute_response.status_code == 409

    final = client.get(f"/action-points/{action_point_id}")
    assert final.json()["status"] == "REJECTED"

    audit_response = client.get(f"/audit-log?action_point_id={action_point_id}")
    event_types = [entry["event_type"] for entry in audit_response.json()]
    assert event_types == ["PROPOSED", "REJECTED"]


def test_execution_impossible_without_explicit_approval(client) -> None:
    create_response = client.post(
        "/action-points",
        json={"transcript": "process a payment for the vendor", "confidence": 0.9},
    )
    action_point_id = create_response.json()["id"]

    response = client.post(f"/action-points/{action_point_id}/execute")
    assert response.status_code == 409

    final = client.get(f"/action-points/{action_point_id}")
    assert final.json()["status"] == "PENDING_APPROVAL"


def test_latency_header_present_on_responses(client) -> None:
    response = client.get("/health")
    assert "X-Process-Time-Ms" in response.headers
