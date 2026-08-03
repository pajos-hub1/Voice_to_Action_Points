import pytest

from approval.gate import InvalidTransition, approve, reject
from audit.log import AuditLogModel
from orchestration.action_points import ActionPointModel, build_action_point
from orchestration.enums import ActionPointStatus, RiskLevel
from orchestration.intent import IntentResult


def _make_action_point_row(db_session) -> ActionPointModel:
    intent_result = IntentResult(intent="schedule_meeting", risk_level=RiskLevel.LOW)
    action_point = build_action_point("schedule a meeting", 0.9, intent_result)
    row = ActionPointModel(**action_point.model_dump())
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_approve_transitions_to_approved_and_writes_audit_event(db_session) -> None:
    row = _make_action_point_row(db_session)

    approved = approve(db_session, row, approver="alice")

    assert approved.status == ActionPointStatus.APPROVED.value
    assert approved.approver == "alice"
    assert approved.approved_at is not None

    events = db_session.query(AuditLogModel).filter_by(action_point_id=row.id).all()
    assert any(e.event_type == "APPROVED" for e in events)


def test_reject_transitions_to_rejected_and_writes_audit_event(db_session) -> None:
    row = _make_action_point_row(db_session)

    rejected = reject(db_session, row, approver="bob", reason="not needed")

    assert rejected.status == ActionPointStatus.REJECTED.value
    assert rejected.approver == "bob"

    events = db_session.query(AuditLogModel).filter_by(action_point_id=row.id).all()
    assert any(e.event_type == "REJECTED" for e in events)


def test_cannot_approve_twice(db_session) -> None:
    row = _make_action_point_row(db_session)
    approve(db_session, row, approver="alice")

    with pytest.raises(InvalidTransition):
        approve(db_session, row, approver="alice")


def test_cannot_reject_after_approved(db_session) -> None:
    row = _make_action_point_row(db_session)
    approve(db_session, row, approver="alice")

    with pytest.raises(InvalidTransition):
        reject(db_session, row, approver="bob")


def test_cannot_approve_rejected_action_point(db_session) -> None:
    row = _make_action_point_row(db_session)
    reject(db_session, row, approver="bob")

    with pytest.raises(InvalidTransition):
        approve(db_session, row, approver="alice")
