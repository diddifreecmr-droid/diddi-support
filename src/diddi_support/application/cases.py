from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from diddi_support.domain.cases import CasePriority, CaseStatus, SupportCase
from diddi_support.infrastructure.persistence.repository import PostgresSupportCaseRepository


class PersistentSupportCaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PostgresSupportCaseRepository(session)

    async def open_case(
        self,
        *,
        origin_service: str,
        resource_type: str,
        resource_id: UUID,
        reporter_user_id: UUID,
        category: str,
        subject: str,
        idempotency_key: str,
        origin_report_id: str | None,
        priority: CasePriority,
        request_id: str | None,
    ) -> tuple[SupportCase, bool]:
        payload: dict[str, Any] = {
            "origin_service": origin_service,
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "reporter_user_id": str(reporter_user_id),
            "category": category,
            "subject": subject,
            "origin_report_id": origin_report_id,
            "priority": priority.value,
        }
        case = SupportCase(
            origin_service=origin_service,
            resource_type=resource_type,
            resource_id=resource_id,
            reporter_user_id=reporter_user_id,
            category=category,
            subject=subject,
            origin_report_id=origin_report_id,
            priority=priority,
        )
        return await self.repository.create_or_get(
            case,
            request_payload=payload,
            idempotency_key=idempotency_key,
            request_id=request_id,
        )

    async def get(self, case_id: UUID) -> SupportCase | None:
        return await self.repository.get(case_id)

    async def list(
        self,
        *,
        status: CaseStatus | None = None,
        priority: CasePriority | None = None,
        limit: int = 50,
    ) -> list[SupportCase]:
        return await self.repository.list(status=status, priority=priority, limit=limit)

    async def assign_case(
        self,
        case_id: UUID,
        agent_id: UUID,
        *,
        actor_id: str,
        request_id: str | None,
    ) -> SupportCase | None:
        case = await self.get(case_id)
        if case is None:
            return None
        case.assign(agent_id)
        return await self.repository.save_update(
            case,
            action="support.case.assigned",
            actor_id=actor_id,
            request_id=request_id,
            metadata={"agent_id": str(agent_id)},
        )

    async def transition_case(
        self,
        case_id: UUID,
        new_status: CaseStatus,
        *,
        actor_id: str,
        request_id: str | None,
    ) -> SupportCase | None:
        case = await self.get(case_id)
        if case is None:
            return None
        case.transition_to(new_status)
        return await self.repository.save_update(
            case,
            action="support.case.status_changed",
            actor_id=actor_id,
            request_id=request_id,
            metadata={"status": new_status.value},
        )
