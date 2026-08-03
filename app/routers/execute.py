from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from executor.run import ExecutionFailed, ExecutionNotAllowed
from executor.run import execute as run_executor
from orchestration.action_points import ActionPoint, ActionPointModel

router = APIRouter(prefix="/action-points", tags=["execution"])


def _get_action_point_or_404(db: Session, action_point_id: str) -> ActionPointModel:
    row = db.get(ActionPointModel, action_point_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Action point not found")
    return row


@router.post("/{action_point_id}/execute", response_model=ActionPoint)
def execute_action_point(action_point_id: str, db: Session = Depends(get_db)) -> ActionPoint:
    row = _get_action_point_or_404(db, action_point_id)
    try:
        row = run_executor(db, row)
    except ExecutionNotAllowed as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ExecutionFailed as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return ActionPoint.model_validate(row)
