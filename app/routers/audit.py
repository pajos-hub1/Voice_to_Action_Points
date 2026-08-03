from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from audit.log import AuditLogEntry, AuditLogModel

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("", response_model=list[AuditLogEntry])
def list_audit_log(action_point_id: str | None = None, db: Session = Depends(get_db)) -> list[AuditLogEntry]:
    query = db.query(AuditLogModel)
    if action_point_id is not None:
        query = query.filter(AuditLogModel.action_point_id == action_point_id)
    rows = query.order_by(AuditLogModel.timestamp.asc()).all()
    return [AuditLogEntry.model_validate(row) for row in rows]
