import pytest

from approval.gate import approve
from audit.log import AuditLogModel
from executor.run import ExecutionFailed, ExecutionNotAllowed, execute
from orchestration.action_points import ActionPointModel, build_action_point
from orchestration.enums import ActionPointStatus, RiskLevel
from orchestration.intent import IntentResult


def _make_row(db_session, intent: str = "schedule_meeting") -> ActionPointModel:
    intent_result = IntentResult(intent=intent, risk_level=RiskLevel.LOW)
    action_point = build_action_point("schedule a meeting", 0.9, intent_result)
    row = ActionPointModel(**action_point.model_dump())
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_execute_approved_action_point_succeeds(db_session) -> None:
    row = _make_row(db_session)
    approve(db_session, row, approver="alice")

    executed = execute(db_session, row)

    assert executed.status == ActionPointStatus.EXECUTED.value
    assert executed.execution_result is not None
    assert executed.executed_at is not None

    events = db_session.query(AuditLogModel).filter_by(action_point_id=row.id).all()
    assert any(e.event_type == "EXECUTED" for e in events)


def test_execute_rejects_action_point_not_approved(db_session) -> None:
    row = _make_row(db_session)

    with pytest.raises(ExecutionNotAllowed):
        execute(db_session, row)


def test_execute_unknown_intent_fails_and_leaves_status_approved(db_session) -> None:
    row = _make_row(db_session, intent="unknown")
    approve(db_session, row, approver="alice")

    with pytest.raises(ExecutionFailed):
        execute(db_session, row)

    assert row.status == ActionPointStatus.APPROVED.value

    events = db_session.query(AuditLogModel).filter_by(action_point_id=row.id).all()
    assert any(e.event_type == "EXECUTION_FAILED" for e in events)
