from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

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


def execute(db: Session, action_point: ActionPointModel, actor: str = "system") -> ActionPointModel:
    # Re-checked here, independent of any router-level check — approval can't be bypassed
    # by calling this function directly.
    if action_point.status != ActionPointStatus.APPROVED.value:
        raise ExecutionNotAllowed(
            f"Cannot execute Action Point {action_point.id} from status {action_point.status!r}; "
            f"only {ActionPointStatus.APPROVED.value} can be executed."
        )

    handler = MOCK_INTEGRATIONS.get(action_point.intent)
    if handler is None:
        record_event(
            db,
            action_point_id=action_point.id,
            event_type="EXECUTION_FAILED",
            actor=actor,
            payload={"error": f"No mock integration registered for intent {action_point.intent!r}"},
        )
        raise ExecutionFailed(f"No mock integration registered for intent {action_point.intent!r}")

    try:
        result = handler(action_point)
    except Exception as error:  # noqa: BLE001 — any handler failure must be recorded, not just known types
        record_event(
            db,
            action_point_id=action_point.id,
            event_type="EXECUTION_FAILED",
            actor=actor,
            payload={"error": str(error)},
        )
        raise ExecutionFailed(str(error)) from error

    action_point.status = ActionPointStatus.EXECUTED.value
    action_point.executed_at = datetime.now(timezone.utc)
    action_point.execution_result = result
    db.add(action_point)
    db.commit()
    db.refresh(action_point)

    record_event(
        db,
        action_point_id=action_point.id,
        event_type="EXECUTED",
        actor=actor,
        payload={"intent": action_point.intent, "result": result},
    )
    return action_point
