from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_intent_extractor_dep
from orchestration.action_points import ActionPoint, ActionPointModel, build_action_point
from orchestration.enums import ActionPointStatus
from orchestration.intent import IntentExtractor

router = APIRouter(prefix="/action-points", tags=["action-points"])


class CreateActionPointRequest(BaseModel):
    transcript: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


@router.post("", response_model=ActionPoint, status_code=status.HTTP_201_CREATED)
def create_action_point(
    payload: CreateActionPointRequest,
    db: Session = Depends(get_db),
    intent_extractor: IntentExtractor = Depends(get_intent_extractor_dep),
) -> ActionPoint:
    intent_result = intent_extractor.extract(payload.transcript)
    action_point = build_action_point(payload.transcript, payload.confidence, intent_result)

    row = ActionPointModel(**action_point.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ActionPoint.model_validate(row)


@router.get("", response_model=list[ActionPoint])
def list_action_points(
    status_filter: ActionPointStatus | None = None,
    db: Session = Depends(get_db),
) -> list[ActionPoint]:
    query = db.query(ActionPointModel)
    if status_filter is not None:
        query = query.filter(ActionPointModel.status == status_filter.value)
    rows = query.order_by(ActionPointModel.created_at.desc()).all()
    return [ActionPoint.model_validate(row) for row in rows]


@router.get("/{action_point_id}", response_model=ActionPoint)
def get_action_point(action_point_id: str, db: Session = Depends(get_db)) -> ActionPoint:
    row = db.get(ActionPointModel, action_point_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Action point not found")
    return ActionPoint.model_validate(row)
