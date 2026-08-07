from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from audit.log import record_event
from orchestration.action_points import ActionPointModel
from orchestration.enums import ActionPointStatus


class InvalidTransition(RuntimeError):
    """Raised when approve/reject is attempted from a status other than PENDING_APPROVAL."""


def _current_status(db: Session, action_point_id: str) -> str:
    row = db.get(ActionPointModel, action_point_id)
    return row.status if row is not None else "<deleted>"


def approve(db: Session, action_point: ActionPointModel, approver: str) -> ActionPointModel:
    action_point_id = action_point.id
    # Guarded UPDATE: the status is re-checked atomically at write time, so two
    # concurrent approves can't both pass — only one wins the row, the other
    # matches zero rows and fails.
    result = db.execute(
        update(ActionPointModel)
        .where(
            ActionPointModel.id == action_point_id,
            ActionPointModel.status == ActionPointStatus.PENDING_APPROVAL.value,
        )
        .values(
            status=ActionPointStatus.APPROVED.value,
            approver=approver,
            approved_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise InvalidTransition(
            f"Cannot approve Action Point {action_point_id} from status {_current_status(db, action_point_id)!r}; "
            f"only {ActionPointStatus.PENDING_APPROVAL.value} can be approved."
        )

    record_event(
        db,
        action_point_id=action_point_id,
        event_type="APPROVED",
        actor=approver,
        payload={"transcript": action_point.transcript, "intent": action_point.intent},
    )

    db.commit()
    db.refresh(action_point)
    return action_point


def reject(db: Session, action_point: ActionPointModel, approver: str, reason: str | None = None) -> ActionPointModel:
    action_point_id = action_point.id
    result = db.execute(
        update(ActionPointModel)
        .where(
            ActionPointModel.id == action_point_id,
            ActionPointModel.status == ActionPointStatus.PENDING_APPROVAL.value,
        )
        .values(status=ActionPointStatus.REJECTED.value, approver=approver)
    )
    if result.rowcount == 0:
        db.rollback()
        raise InvalidTransition(
            f"Cannot reject Action Point {action_point_id} from status {_current_status(db, action_point_id)!r}; "
            f"only {ActionPointStatus.PENDING_APPROVAL.value} can be rejected."
        )

    record_event(
        db,
        action_point_id=action_point_id,
        event_type="REJECTED",
        actor=approver,
        payload={"transcript": action_point.transcript, "intent": action_point.intent, "reason": reason},
    )

    db.commit()
    db.refresh(action_point)
    return action_point
