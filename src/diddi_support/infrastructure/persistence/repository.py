from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from diddi_support.domain.cases import (
    CasePriority,
    CaseStatus,
    DomainConflictError,
    SupportCase,
    _fingerprint,
)
from diddi_support.infrastructure.persistence.models import (
    SupportAuditEventModel,
    SupportCaseModel,
    SupportCaseOperationModel,
    SupportOutboxEventModel,
)


class PostgresSupportCaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, case_id: UUID) -> SupportCase | None:
        model = await self.session.get(SupportCaseModel, case_id)
        return _to_domain(model) if model is not None else None

    async def list(
        self,
        *,
        status: CaseStatus | None = None,
        priority: CasePriority | None = None,
        limit: int = 50,
    ) -> list[SupportCase]:
        statement = select(SupportCaseModel).order_by(SupportCaseModel.created_at).limit(limit)
        if status is not None:
            statement = statement.where(SupportCaseModel.status == status.value)
        if priority is not None:
            statement = statement.where(SupportCaseModel.priority == priority.value)
        result = await self.session.execute(statement)
        return [_to_domain(model) for model in result.scalars().all()]

    async def save_update(
        self,
        case: SupportCase,
        *,
        action: str,
        actor_id: str,
        request_id: str | None,
        metadata: dict[str, Any],
    ) -> SupportCase:
        model = await self.session.get(SupportCaseModel, case.id)
        if model is None:
            return case
        model.assigned_agent_id = case.assigned_agent_id
        model.priority = case.priority.value
        model.status = case.status.value
        model.updated_at = case.updated_at
        model.resolved_at = case.resolved_at
        self.session.add(
            SupportAuditEventModel(
                id=uuid4(),
                action=action,
                target_type="support_case",
                target_id=str(case.id),
                outcome="succeeded",
                actor_id=None,
                request_id=request_id,
                metadata_json={**metadata, "actor_id": actor_id},
                occurred_at=datetime.now(UTC),
            )
        )
        self.session.add(
            SupportOutboxEventModel(
                id=uuid4(),
                event_type=action,
                aggregate_type="support_case",
                aggregate_id=str(case.id),
                payload={
                    "status": case.status.value,
                    "assigned_agent_id": str(case.assigned_agent_id)
                    if case.assigned_agent_id
                    else None,
                },
                correlation_id=request_id,
                created_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        return case

    async def record_context_access(
        self,
        *,
        resource_type: str,
        resource_id: UUID,
        actor_id: str,
        request_id: str | None,
        fetched_at: datetime,
    ) -> None:
        self.session.add(
            SupportAuditEventModel(
                id=uuid4(),
                action="support.context.read",
                target_type=resource_type,
                target_id=str(resource_id),
                outcome="succeeded",
                actor_id=None,
                request_id=request_id,
                metadata_json={"actor_id": actor_id, "fetched_at": fetched_at.isoformat()},
                occurred_at=datetime.now(UTC),
            )
        )
        await self.session.commit()

    async def create_or_get(
        self,
        case: SupportCase,
        *,
        request_payload: dict[str, Any],
        idempotency_key: str,
        request_id: str | None,
    ) -> tuple[SupportCase, bool]:
        fingerprint = _fingerprint(request_payload)
        async with self.session.begin():
            operation_insert = insert(SupportCaseOperationModel).values(
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                case_id=case.id,
                created_at=datetime.now(UTC),
            ).on_conflict_do_nothing(index_elements=[SupportCaseOperationModel.idempotency_key])
            result = await self.session.execute(operation_insert)
            if result.rowcount == 0:
                operation = await self.session.scalar(
                    select(SupportCaseOperationModel).where(
                        SupportCaseOperationModel.idempotency_key == idempotency_key
                    )
                )
                if operation is None or operation.fingerprint != fingerprint:
                    raise DomainConflictError("IDEMPOTENCY_CONFLICT")
                existing = await self.session.get(SupportCaseModel, operation.case_id)
                if existing is None:
                    raise RuntimeError("support case operation points to missing case")
                return _to_domain(existing), False

            self.session.add(_case_model(case))
            self.session.add(
                SupportAuditEventModel(
                    id=case.id,
                    action="support.case.created",
                    target_type="support_case",
                    target_id=str(case.id),
                    outcome="succeeded",
                    actor_id=case.reporter_user_id,
                    request_id=request_id,
                    metadata_json={
                        "origin_service": case.origin_service,
                        "resource_type": case.resource_type,
                    },
                    occurred_at=datetime.now(UTC),
                )
            )
            self.session.add(
                SupportOutboxEventModel(
                    id=case.id,
                    event_type="support.case.created",
                    aggregate_type="support_case",
                    aggregate_id=str(case.id),
                    payload={
                        "origin_service": case.origin_service,
                        "resource_type": case.resource_type,
                        "resource_id": str(case.resource_id),
                        "priority": case.priority.value,
                    },
                    correlation_id=request_id,
                    created_at=datetime.now(UTC),
                )
            )
        return case, True


def _case_model(case: SupportCase) -> SupportCaseModel:
    return SupportCaseModel(
        id=case.id,
        origin_service=case.origin_service,
        resource_type=case.resource_type,
        resource_id=case.resource_id,
        origin_report_id=case.origin_report_id,
        reporter_user_id=case.reporter_user_id,
        category=case.category,
        subject=case.subject,
        priority=case.priority.value,
        status=case.status.value,
        assigned_agent_id=case.assigned_agent_id,
        resolution_code=case.resolution_code,
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
    )


def _to_domain(model: SupportCaseModel) -> SupportCase:
    return SupportCase(
        id=model.id,
        origin_service=model.origin_service,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        origin_report_id=model.origin_report_id,
        reporter_user_id=model.reporter_user_id,
        category=model.category,
        subject=model.subject,
        priority=CasePriority(model.priority),
        status=model.status,
        assigned_agent_id=model.assigned_agent_id,
        resolution_code=model.resolution_code,
        created_at=model.created_at,
        updated_at=model.updated_at,
        resolved_at=model.resolved_at,
    )
