from orchestration.enums import ActionPointStatus, RiskLevel


def test_create_action_point(client) -> None:
    response = client.post(
        "/action-points",
        json={"transcript": "please schedule a meeting with the design team", "confidence": 0.91},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["intent"] == "schedule_meeting"
    assert body["risk_level"] == RiskLevel.LOW.value
    assert body["status"] == ActionPointStatus.PENDING_APPROVAL.value
    assert body["confidence"] == 0.91
    assert body["id"]


def test_create_action_point_rejects_out_of_range_confidence(client) -> None:
    response = client.post("/action-points", json={"transcript": "schedule a meeting", "confidence": 1.5})
    assert response.status_code == 422


def test_list_and_get_action_point(client) -> None:
    create_response = client.post(
        "/action-points",
        json={"transcript": "send an email to finance", "confidence": 0.88},
    )
    action_point_id = create_response.json()["id"]

    list_response = client.get("/action-points")
    assert list_response.status_code == 200
    assert any(item["id"] == action_point_id for item in list_response.json())

    get_response = client.get(f"/action-points/{action_point_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == action_point_id


def test_get_missing_action_point_returns_404(client) -> None:
    response = client.get("/action-points/does-not-exist")
    assert response.status_code == 404
