def _create_action_point(client, transcript: str = "schedule a meeting", confidence: float = 0.9) -> str:
    response = client.post("/action-points", json={"transcript": transcript, "confidence": confidence})
    return response.json()["id"]


def test_approve_endpoint_happy_path(client) -> None:
    action_point_id = _create_action_point(client)

    response = client.post(f"/action-points/{action_point_id}/approve", json={"approver": "alice"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["approver"] == "alice"


def test_reject_endpoint_happy_path(client) -> None:
    action_point_id = _create_action_point(client)

    response = client.post(
        f"/action-points/{action_point_id}/reject",
        json={"approver": "bob", "reason": "duplicate"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_approve_twice_returns_409(client) -> None:
    action_point_id = _create_action_point(client)
    client.post(f"/action-points/{action_point_id}/approve", json={"approver": "alice"})

    response = client.post(f"/action-points/{action_point_id}/approve", json={"approver": "alice"})
    assert response.status_code == 409


def test_reject_after_approve_returns_409(client) -> None:
    action_point_id = _create_action_point(client)
    client.post(f"/action-points/{action_point_id}/approve", json={"approver": "alice"})

    response = client.post(f"/action-points/{action_point_id}/reject", json={"approver": "bob"})
    assert response.status_code == 409


def test_approve_missing_action_point_returns_404(client) -> None:
    response = client.post("/action-points/does-not-exist/approve", json={"approver": "alice"})
    assert response.status_code == 404
