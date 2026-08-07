from datetime import datetime, timezone

from sqlalchemy.orm import Session

from audit.log import record_event
from orchestration.action_points import ActionPointModel
from orchestration.enums import ActionPointStatus


class InvalidTransition(RuntimeError):
    """Raised when approve/reject is attempted from a status other than PENDING_APPROVAL."""


def approve(db: Session, action_point: ActionPointModel, approver: str) -> ActionPointModel:
    if action_point.status != ActionPointStatus.PENDING_APPROVAL.value:
        raise InvalidTransition(
            f"Cannot approve Action Point {action_point.id} from status {action_point.status!r}; "
            f"only {ActionPointStatus.PENDING_APPROVAL.value} can be approved."
        )

    action_point.status = ActionPointStatus.APPROVED.value
    action_point.approver = approver
    action_point.approved_at = datetime.now(timezone.utc)
    db.add(action_point)

    record_event(
        db,
        action_point_id=action_point.id,
        event_type="APPROVED",
        actor=approver,
        payload={"transcript": action_point.transcript, "intent": action_point.intent},
    )

    db.commit()
    db.refresh(action_point)
    return action_point


def reject(db: Session, action_point: ActionPointModel, approver: str, reason: str | None = None) -> ActionPointModel:
    if action_point.status != ActionPointStatus.PENDING_APPROVAL.value:
        raise InvalidTransition(
            f"Cannot reject Action Point {action_point.id} from status {action_point.status!r}; "
            f"only {ActionPointStatus.PENDING_APPROVAL.value} can be rejected."
        )

    action_point.status = ActionPointStatus.REJECTED.value
    action_point.approver = approver
    db.add(action_point)

    record_event(
        db,
        action_point_id=action_point.id,
        event_type="REJECTED",
        actor=approver,
        payload={"transcript": action_point.transcript, "intent": action_point.intent, "reason": reason},
    )

    db.commit()
    db.refresh(action_point)
    return action_point
