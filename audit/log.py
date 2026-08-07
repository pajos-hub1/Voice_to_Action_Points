import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base


class AuditLogModel(Base):
    """Append-only audit trail. No update/delete path exists anywhere in this codebase —
    record_event() is the only way to write to this table."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    action_point_id: Mapped[str] = mapped_column(String, ForeignKey("action_points.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action_point_id: str
    event_type: str
    actor: str
    payload: dict[str, Any]
    timestamp: datetime


def record_event(
    db: Session,
    action_point_id: str,
    event_type: str,
    actor: str,
    payload: dict[str, Any] | None = None,
) -> AuditLogModel:
    entry = AuditLogModel(
        id=str(uuid.uuid4()),
        action_point_id=action_point_id,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
        timestamp=datetime.now(timezone.utc),
    )
    # No commit here: the caller's state mutation and this audit write must land
    # in the SAME transaction, so a crash can't leave one without the other.
    db.add(entry)
    return entry
