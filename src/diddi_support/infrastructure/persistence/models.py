from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SupportCaseModel(Base):
    __tablename__ = "support_cases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    origin_service: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    origin_report_id: Mapped[str | None] = mapped_column(String(160))
    reporter_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    category: Mapped[str] = mapped_column(String(80))
    subject: Mapped[str] = mapped_column(String(200))
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(32))
    assigned_agent_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    resolution_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupportCaseOperationModel(Base):
    __tablename__ = "support_case_operations"
    __table_args__ = (UniqueConstraint("idempotency_key", name="support_case_operations_key_uq"),)

    idempotency_key: Mapped[str] = mapped_column(String(160), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SupportAuditEventModel(Base):
    __tablename__ = "support_audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    action: Mapped[str] = mapped_column(String(120))
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(160))
    outcome: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    request_id: Mapped[str | None] = mapped_column(String(160))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SupportOutboxEventModel(Base):
    __tablename__ = "support_outbox_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(160))
    aggregate_type: Mapped[str] = mapped_column(String(80))
    aggregate_id: Mapped[str] = mapped_column(String(160))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    correlation_id: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
