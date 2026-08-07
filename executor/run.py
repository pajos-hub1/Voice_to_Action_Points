from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from audit.log import record_event
from orchestration.action_points import ActionPointModel
from orchestration.enums import ActionPointStatus


class ExecutionNotAllowed(RuntimeError):
    """Raised when execute() is called on an Action Point that isn't APPROVED."""


class ExecutionFailed(RuntimeError):
    """Raised when a mock integration handler fails, or none is registered for the intent."""


def _handle_send_email(action_point: ActionPointModel) -> dict[str, Any]:
    return {"status": "sent", "message_id": f"mock-email-{action_point.id[:8]}"}


def _handle_schedule_meeting(action_point: ActionPointModel) -> dict[str, Any]:
    return {"status": "scheduled", "event_id": f"mock-event-{action_point.id[:8]}"}


def _handle_create_ticket(action_point: ActionPointModel) -> dict[str, Any]:
    return {"status": "created", "ticket_id": f"mock-ticket-{action_point.id[:8]}"}


def _handle_delete_resource(action_point: ActionPointModel) -> dict[str, Any]:
    return {"status": "deleted", "resource": action_point.entities.get("raw_transcript", "")}


def _handle_process_payment(action_point: ActionPointModel) -> dict[str, Any]:
    return {"status": "paid", "transaction_id": f"mock-txn-{action_point.id[:8]}"}


MOCK_INTEGRATIONS: dict[str, Callable[[ActionPointModel], dict[str, Any]]] = {
    "send_email": _handle_send_email,
    "schedule_meeting": _handle_schedule_meeting,
    "create_ticket": _handle_create_ticket,
    "delete_resource": _handle_delete_resource,
    "process_payment": _handle_process_payment,
}


def _current_status(db: Session, action_point_id: str) -> str:
    row = db.get(ActionPointModel, action_point_id)
    return row.status if row is not None else "<deleted>"


def _revert_claim(db: Session, action_point_id: str, actor: str, error: str) -> None:
    db.execute(
        update(ActionPointModel)
        .where(
            ActionPointModel.id == action_point_id,
            ActionPointModel.status == ActionPointStatus.EXECUTED.value,
        )
        .values(status=ActionPointStatus.APPROVED.value, executed_at=None, execution_result=None)
    )
    record_event(
        db,
        action_point_id=action_point_id,
        event_type="EXECUTION_FAILED",
        actor=actor,
        payload={"error": error},
    )
    db.commit()


def execute(db: Session, action_point: ActionPointModel, actor: str = "system") -> ActionPointModel:
    # Re-checked here, independent of any router-level check — approval can't be bypassed
    # by calling this function directly. The APPROVED->EXECUTED transition is an atomic
    # guarded UPDATE, so two concurrent executes can't both run the integration.
    action_point_id = action_point.id
    claim = db.execute(
        update(ActionPointModel)
        .where(
            ActionPointModel.id == action_point_id,
            ActionPointModel.status == ActionPointStatus.APPROVED.value,
        )
        .values(status=ActionPointStatus.EXECUTED.value, executed_at=datetime.now(timezone.utc))
    )
    if claim.rowcount == 0:
        db.rollback()
        raise ExecutionNotAllowed(
            f"Cannot execute Action Point {action_point_id} from status {_current_status(db, action_point_id)!r}; "
            f"only {ActionPointStatus.APPROVED.value} can be executed."
        )

    handler = MOCK_INTEGRATIONS.get(action_point.intent)
    if handler is None:
        error = f"No mock integration registered for intent {action_point.intent!r}"
        _revert_claim(db, action_point_id, actor, error)
        raise ExecutionFailed(error)

    try:
        result = handler(action_point)
    except Exception as error:  # noqa: BLE001 — any handler failure must be recorded, not just known types
        _revert_claim(db, action_point_id, actor, str(error))
        raise ExecutionFailed(str(error)) from error

    finalized = db.execute(
        update(ActionPointModel)
        .where(
            ActionPointModel.id == action_point_id,
            ActionPointModel.status == ActionPointStatus.EXECUTED.value,
        )
        .values(execution_result=result)
    )
    if finalized.rowcount == 0:  # pragma: no cover - only reachable if the claim was reverted concurrently
        db.rollback()
        raise ExecutionFailed("Execution claim was lost before the result could be recorded.")

    record_event(
        db,
        action_point_id=action_point_id,
        event_type="EXECUTED",
        actor=actor,
        payload={"intent": action_point.intent, "result": result},
    )

    db.commit()
    db.refresh(action_point)
    return action_point
