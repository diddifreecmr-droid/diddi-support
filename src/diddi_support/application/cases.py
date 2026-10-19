from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from diddi_support.domain.cases import CasePriority, SupportCase
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
