from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from diddi_support.domain.sos import SosAlert
from diddi_support.infrastructure.persistence.repository import PostgresSupportCaseRepository


class SosService:
    def __init__(self) -> None:
        self.alerts: dict[UUID, SosAlert] = {}
        self.by_source_alert: dict[tuple[str, str], UUID] = {}

    def create(self, alert: SosAlert) -> tuple[SosAlert, bool]:
        if alert.source_alert_id is not None:
            key = (alert.origin_service, alert.source_alert_id)
            existing_id = self.by_source_alert.get(key)
            if existing_id is not None:
                return self.alerts[existing_id], False
            self.by_source_alert[key] = alert.id
        self.alerts[alert.id] = alert
        return alert, True

    def get(self, alert_id: UUID) -> SosAlert | None:
        return self.alerts.get(alert_id)

    def queue(self, *, limit: int = 50) -> list[SosAlert]:
        return sorted(
            (
                alert
                for alert in self.alerts.values()
                if alert.handling_status != "completed"
            ),
            key=lambda alert: (alert.escalation_level, alert.created_at),
        )[:limit]


class PersistentSosService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PostgresSupportCaseRepository(session)

    async def create(self, alert: SosAlert, *, request_id: str | None = None) -> SosAlert:
        return await self.repository.add_sos_alert(alert, request_id=request_id)

    async def get(self, alert_id: UUID) -> SosAlert | None:
        return await self.repository.get_sos_alert(alert_id)

    async def queue(self, *, limit: int = 50) -> list[SosAlert]:
        return await self.repository.list_sos_alerts(limit=limit)

    async def save(
        self,
        alert: SosAlert,
        *,
        action: str,
        actor_id: str,
        request_id: str | None = None,
    ) -> SosAlert:
        return await self.repository.save_sos_alert(
            alert,
            action=action,
            actor_id=actor_id,
            request_id=request_id,
        )
