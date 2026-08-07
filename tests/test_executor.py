import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Any

from app.db import Base
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


def test_execute_is_atomic_with_audit_write(db_session, monkeypatch) -> None:
    row = _make_row(db_session)
    approve(db_session, row, approver="alice")

    def fail_audit_write(*args, **kwargs):
        raise RuntimeError("audit write failed")

    monkeypatch.setattr("executor.run.record_event", fail_audit_write)

    with pytest.raises(RuntimeError):
        execute(db_session, row)

    db_session.rollback()  # simulates the DB rolling back a transaction closed mid-write
    fresh = db_session.get(ActionPointModel, row.id)
    assert fresh.status == ActionPointStatus.APPROVED.value
    assert fresh.execution_result is None
    events = db_session.query(AuditLogModel).filter_by(action_point_id=row.id).all()
    assert [e.event_type for e in events] == ["APPROVED"]


def test_concurrent_execute_runs_integration_once(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    def counting_handler(action_point: ActionPointModel) -> dict[str, Any]:
        calls.append(action_point.id)
        return {"status": "scheduled"}

    monkeypatch.setattr("executor.run.MOCK_INTEGRATIONS", {"schedule_meeting": counting_handler})

    engine = create_engine(
        f"sqlite:///{tmp_path / 'race_execute.db'}",
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
        approve(s1, row_a, approver="alice")

        row_b = s2.get(ActionPointModel, row.id)
        s2.commit()  # release s2's read lock; row_b is now a stale APPROVED snapshot

        executed = execute(s1, row_a)
        assert executed.status == ActionPointStatus.EXECUTED.value

        with pytest.raises(ExecutionNotAllowed):
            execute(s2, row_b)

        assert len(calls) == 1
        executed_events = (
            s1.query(AuditLogModel).filter_by(action_point_id=row.id, event_type="EXECUTED").all()
        )
        assert len(executed_events) == 1
    finally:
        s1.close()
        s2.close()
        engine.dispose()
