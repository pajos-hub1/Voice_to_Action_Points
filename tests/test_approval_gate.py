import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
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


def test_approve_is_atomic_with_audit_write(db_session, monkeypatch) -> None:
    row = _make_action_point_row(db_session)

    def fail_audit_write(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr("approval.gate.record_event", fail_audit_write)

    with pytest.raises(RuntimeError):
        approve(db_session, row, approver="alice")

    db_session.rollback()  # simulates the DB rolling back a transaction closed mid-write
    fresh = db_session.get(ActionPointModel, row.id)
    assert fresh.status == ActionPointStatus.PENDING_APPROVAL.value
    assert fresh.approver is None
    assert db_session.query(AuditLogModel).filter_by(action_point_id=row.id).count() == 0


def test_concurrent_approve_only_one_wins(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    s1 = sessionmaker(bind=engine, expire_on_commit=False)()
    s2 = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        intent_result = IntentResult(intent="schedule_meeting", risk_level=RiskLevel.LOW)
        action_point = build_action_point("schedule a meeting", 0.9, intent_result)
        row = ActionPointModel(**action_point.model_dump())
        s1.add(row)
        s1.commit()

        row_a = s1.get(ActionPointModel, row.id)
        row_b = s2.get(ActionPointModel, row.id)
        s2.commit()  # release s2's read lock; row_b is now a stale PENDING_APPROVAL snapshot

        approve(s1, row_a, approver="alice")
        with pytest.raises(InvalidTransition):
            approve(s2, row_b, approver="bob")

        approved_events = (
            s1.query(AuditLogModel).filter_by(action_point_id=row.id, event_type="APPROVED").all()
        )
        assert len(approved_events) == 1
        assert s1.get(ActionPointModel, row.id).approver == "alice"
    finally:
        s1.close()
        s2.close()
        engine.dispose()
