from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from approval.gate import InvalidTransition
from approval.gate import approve as approve_gate
from approval.gate import reject as reject_gate
from orchestration.action_points import ActionPoint, ActionPointModel

router = APIRouter(prefix="/action-points", tags=["approval"])

# Sync def: the approval gate performs blocking DB writes and audit inserts. FastAPI
# runs these handlers in a threadpool, so the event loop is never blocked.


class ApprovalRequest(BaseModel):
    approver: str = Field(min_length=1)


class RejectionRequest(BaseModel):
    approver: str = Field(min_length=1)
    reason: str | None = None


def _get_action_point_or_404(db: Session, action_point_id: str) -> ActionPointModel:
    row = db.get(ActionPointModel, action_point_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Action point not found")
    return row


@router.post("/{action_point_id}/approve", response_model=ActionPoint)
def approve_action_point(
    action_point_id: str,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
) -> ActionPoint:
    row = _get_action_point_or_404(db, action_point_id)
    try:
        row = approve_gate(db, row, payload.approver)
    except InvalidTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return ActionPoint.model_validate(row)


@router.post("/{action_point_id}/reject", response_model=ActionPoint)
def reject_action_point(
    action_point_id: str,
    payload: RejectionRequest,
    db: Session = Depends(get_db),
) -> ActionPoint:
    row = _get_action_point_or_404(db, action_point_id)
    try:
        row = reject_gate(db, row, payload.approver, payload.reason)
    except InvalidTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return ActionPoint.model_validate(row)
