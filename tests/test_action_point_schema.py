import pytest
from pydantic import ValidationError

from orchestration.action_points import ActionPoint, build_action_point
from orchestration.enums import ActionPointStatus, RiskLevel
from orchestration.intent import IntentResult


def test_build_action_point_from_intent_result() -> None:
    intent_result = IntentResult(
        intent="schedule_meeting",
        entities={"raw_transcript": "schedule a meeting"},
        risk_level=RiskLevel.LOW,
    )

    action_point = build_action_point("schedule a meeting", 0.91, intent_result)

    assert action_point.status == ActionPointStatus.PENDING_APPROVAL
    assert action_point.intent == "schedule_meeting"
    assert action_point.risk_level == RiskLevel.LOW
    assert action_point.confidence == 0.91
    assert action_point.id


@pytest.mark.parametrize(
    "overrides",
    [
        {"confidence": 1.5},
        {"confidence": -0.1},
        {"transcript": ""},
        {"intent": ""},
    ],
)
def test_action_point_rejects_malformed_fields(overrides) -> None:
    base = {
        "id": "test-id",
        "transcript": "schedule a meeting",
        "confidence": 0.9,
        "intent": "schedule_meeting",
        "entities": {},
        "risk_level": RiskLevel.LOW,
        "status": ActionPointStatus.PENDING_APPROVAL,
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)

    with pytest.raises(ValidationError):
        ActionPoint.model_validate(base)
