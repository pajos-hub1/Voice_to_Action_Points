import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from orchestration.enums import ActionPointStatus, RiskLevel
from orchestration.intent import IntentResult


class ActionPointModel(Base):
    __tablename__ = "action_points"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    transcript: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    intent: Mapped[str] = mapped_column(String, nullable=False)
    entities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approver: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ActionPoint(BaseModel):
    """Schema-validated Action Point. Constructing one enforces FR-4 (reject malformed output)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    transcript: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    intent: str = Field(min_length=1)
    entities: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel
    status: ActionPointStatus
    created_at: datetime
    approver: str | None = None
    approved_at: datetime | None = None
    executed_at: datetime | None = None
    execution_result: dict[str, Any] | None = None


def build_action_point(transcript: str, confidence: float, intent_result: IntentResult) -> ActionPoint:
    """Combine a transcript + intent result into a validated Action Point, status=PENDING_APPROVAL.

    Raises pydantic.ValidationError if the result doesn't satisfy the schema — malformed
    output must never reach the database or the approval gate.
    """
    return ActionPoint(
        id=str(uuid.uuid4()),
        transcript=transcript,
        confidence=confidence,
        intent=intent_result.intent,
        entities=intent_result.entities,
        risk_level=intent_result.risk_level,
        status=ActionPointStatus.PENDING_APPROVAL,
        created_at=datetime.now(timezone.utc),
    )
