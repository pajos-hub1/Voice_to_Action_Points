def _create_action_point(client, transcript: str = "schedule a meeting", confidence: float = 0.9) -> str:
    response = client.post("/action-points", json={"transcript": transcript, "confidence": confidence})
    return response.json()["id"]


def test_execute_without_approval_returns_409(client) -> None:
    action_point_id = _create_action_point(client)

    response = client.post(f"/action-points/{action_point_id}/execute")
    assert response.status_code == 409


def test_execute_after_approval_succeeds(client) -> None:
    action_point_id = _create_action_point(client)
    client.post(f"/action-points/{action_point_id}/approve", json={"approver": "alice"})

    response = client.post(f"/action-points/{action_point_id}/execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EXECUTED"
    assert body["execution_result"] is not None


def test_execute_unknown_intent_returns_500(client) -> None:
    action_point_id = _create_action_point(client, transcript="what's the weather like")
    client.post(f"/action-points/{action_point_id}/approve", json={"approver": "alice"})

    response = client.post(f"/action-points/{action_point_id}/execute")
    assert response.status_code == 500


def test_execute_missing_action_point_returns_404(client) -> None:
    response = client.post("/action-points/does-not-exist/execute")
    assert response.status_code == 404
