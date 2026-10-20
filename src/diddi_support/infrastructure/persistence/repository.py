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
from diddi_support.domain.messages import (
    AttachmentPurpose,
    MessageAuthorType,
    SupportAttachment,
    SupportMessage,
)
from diddi_support.domain.sos import (
    SosAlert,
    SosHandlingStatus,
    SosNotificationStatus,
)
from diddi_support.infrastructure.persistence.models import (
    SosAlertModel,
    SupportAttachmentModel,
    SupportAuditEventModel,
    SupportCaseModel,
    SupportCaseOperationModel,
    SupportMessageModel,
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

    async def add_message(
        self,
        message: SupportMessage,
        *,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> SupportMessage:
        self.session.add(
            SupportMessageModel(
                id=message.id,
                case_id=message.case_id,
                author_type=message.author_type.value,
                author_id=message.author_id,
                body=message.body,
                visibility=message.visibility,
                created_at=message.created_at,
            )
        )
        self.session.add(
            SupportAuditEventModel(
                id=uuid4(),
                action="support.message.created",
                target_type="support_case_message",
                target_id=str(message.id),
                outcome="succeeded",
                actor_id=None,
                request_id=request_id,
                metadata_json={
                    "actor_id": actor_id,
                    "case_id": str(message.case_id),
                    "visibility": message.visibility,
                },
                occurred_at=datetime.now(UTC),
            )
        )
        self.session.add(
            SupportOutboxEventModel(
                id=uuid4(),
                event_type="support.case.message.created",
                aggregate_type="support_case",
                aggregate_id=str(message.case_id),
                payload={
                    "message_id": str(message.id),
                    "visibility": message.visibility,
                },
                correlation_id=request_id,
                created_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        return message

    async def list_messages(self, case_id: UUID) -> list[SupportMessage]:
        result = await self.session.execute(
            select(SupportMessageModel)
            .where(SupportMessageModel.case_id == case_id)
            .order_by(SupportMessageModel.created_at)
        )
        return [
            SupportMessage(
                id=model.id,
                case_id=model.case_id,
                author_type=MessageAuthorType(model.author_type),
                author_id=model.author_id,
                body=model.body,
                visibility=model.visibility,
                created_at=model.created_at,
            )
            for model in result.scalars().all()
        ]

    async def add_attachment(
        self,
        attachment: SupportAttachment,
        *,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> SupportAttachment:
        self.session.add(
            SupportAttachmentModel(
                id=attachment.id,
                case_id=attachment.case_id,
                file_id=attachment.file_id,
                owner_user_id=attachment.owner_user_id,
                purpose=attachment.purpose.value,
                mime_type=attachment.mime_type,
                size_bytes=attachment.size_bytes,
                created_at=attachment.created_at,
            )
        )
        self.session.add(
            SupportAuditEventModel(
                id=uuid4(),
                action="support.attachment.referenced",
                target_type="support_case_attachment",
                target_id=str(attachment.id),
                outcome="succeeded",
                actor_id=None,
                request_id=request_id,
                metadata_json={
                    "actor_id": actor_id,
                    "case_id": str(attachment.case_id),
                    "file_id": str(attachment.file_id),
                    "purpose": attachment.purpose.value,
                },
                occurred_at=datetime.now(UTC),
            )
        )
        self.session.add(
            SupportOutboxEventModel(
                id=uuid4(),
                event_type="support.case.attachment.referenced",
                aggregate_type="support_case",
                aggregate_id=str(attachment.case_id),
                payload={
                    "attachment_id": str(attachment.id),
                    "file_id": str(attachment.file_id),
                    "purpose": attachment.purpose.value,
                },
                correlation_id=request_id,
                created_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        return attachment

    async def list_attachments(self, case_id: UUID) -> list[SupportAttachment]:
        result = await self.session.execute(
            select(SupportAttachmentModel)
            .where(SupportAttachmentModel.case_id == case_id)
            .order_by(SupportAttachmentModel.created_at)
        )
        return [_attachment_to_domain(model) for model in result.scalars().all()]

    async def get_attachment(self, attachment_id: UUID) -> SupportAttachment | None:
        model = await self.session.get(SupportAttachmentModel, attachment_id)
        return _attachment_to_domain(model) if model is not None else None

    async def add_sos_alert(
        self,
        alert: SosAlert,
        *,
        request_id: str | None = None,
    ) -> SosAlert:
        self.session.add(
            SosAlertModel(
                id=alert.id,
                reporter_user_id=alert.reporter_user_id,
                origin_service=alert.origin_service,
                case_id=alert.case_id,
                source_alert_id=alert.source_alert_id,
                location_latitude=alert.location_latitude,
                location_longitude=alert.location_longitude,
                notification_status=alert.notification_status.value,
                handling_status=alert.handling_status.value,
                source_notification_sent=alert.source_notification_sent,
                notification_attempts=alert.notification_attempts,
                escalation_level=alert.escalation_level,
                created_at=alert.created_at,
                updated_at=alert.updated_at,
            )
        )
        self.session.add(
            SupportAuditEventModel(
                id=uuid4(),
                action="support.sos.created",
                target_type="support_sos_alert",
                target_id=str(alert.id),
                outcome="succeeded",
                actor_id=alert.reporter_user_id,
                request_id=request_id,
                metadata_json={"origin_service": alert.origin_service},
                occurred_at=datetime.now(UTC),
            )
        )
        self.session.add(
            SupportOutboxEventModel(
                id=uuid4(),
                event_type="support.sos.created",
                aggregate_type="support_sos_alert",
                aggregate_id=str(alert.id),
                payload={
                    "origin_service": alert.origin_service,
                    "case_id": str(alert.case_id) if alert.case_id else None,
                    "notification_status": alert.notification_status.value,
                },
                correlation_id=request_id,
                created_at=datetime.now(UTC),
            )
        )
        if not alert.source_notification_sent:
            self.session.add(
                SupportOutboxEventModel(
                    id=uuid4(),
                    event_type="support.sos.notification.requested",
                    aggregate_type="support_sos_alert",
                    aggregate_id=str(alert.id),
                    payload={"notification_attempt": alert.notification_attempts},
                    correlation_id=request_id,
                    created_at=datetime.now(UTC),
                )
            )
        await self.session.commit()
        return alert

    async def get_sos_alert(self, alert_id: UUID) -> SosAlert | None:
        model = await self.session.get(SosAlertModel, alert_id)
        return _sos_to_domain(model) if model is not None else None

    async def list_sos_alerts(self, *, limit: int = 50) -> list[SosAlert]:
        result = await self.session.execute(
            select(SosAlertModel)
            .where(SosAlertModel.handling_status != SosHandlingStatus.COMPLETED.value)
            .order_by(SosAlertModel.escalation_level, SosAlertModel.created_at)
            .limit(limit)
        )
        return [_sos_to_domain(model) for model in result.scalars().all()]

    async def save_sos_alert(
        self,
        alert: SosAlert,
        *,
        action: str,
        actor_id: str,
        request_id: str | None = None,
    ) -> SosAlert:
        model = await self.session.get(SosAlertModel, alert.id)
        if model is None:
            return alert
        model.notification_status = alert.notification_status.value
        model.handling_status = alert.handling_status.value
        model.notification_attempts = alert.notification_attempts
        model.escalation_level = alert.escalation_level
        model.updated_at = alert.updated_at
        self.session.add(
            SupportAuditEventModel(
                id=uuid4(),
                action=action,
                target_type="support_sos_alert",
                target_id=str(alert.id),
                outcome="succeeded",
                actor_id=None,
                request_id=request_id,
                metadata_json={
                    "actor_id": actor_id,
                    "handling_status": alert.handling_status.value,
                },
                occurred_at=datetime.now(UTC),
            )
        )
        self.session.add(
            SupportOutboxEventModel(
                id=uuid4(),
                event_type=action,
                aggregate_type="support_sos_alert",
                aggregate_id=str(alert.id),
                payload={
                    "notification_status": alert.notification_status.value,
                    "handling_status": alert.handling_status.value,
                },
                correlation_id=request_id,
                created_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        return alert

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


def _attachment_to_domain(model: SupportAttachmentModel) -> SupportAttachment:
    return SupportAttachment(
        id=model.id,
        case_id=model.case_id,
        file_id=model.file_id,
        owner_user_id=model.owner_user_id,
        purpose=AttachmentPurpose(model.purpose),
        mime_type=model.mime_type,
        size_bytes=model.size_bytes,
        created_at=model.created_at,
    )


def _sos_to_domain(model: SosAlertModel) -> SosAlert:
    return SosAlert(
        id=model.id,
        reporter_user_id=model.reporter_user_id,
        origin_service=model.origin_service,
        case_id=model.case_id,
        source_alert_id=model.source_alert_id,
        location_latitude=model.location_latitude,
        location_longitude=model.location_longitude,
        source_notification_sent=model.source_notification_sent,
        notification_status=SosNotificationStatus(model.notification_status),
        handling_status=SosHandlingStatus(model.handling_status),
        notification_attempts=model.notification_attempts,
        escalation_level=model.escalation_level,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
