from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from diddi_support.domain.messages import SupportAttachment, SupportMessage
from diddi_support.infrastructure.persistence.repository import PostgresSupportCaseRepository


class SupportConversationService:
    def __init__(self) -> None:
        self.messages: dict[UUID, list[SupportMessage]] = {}
        self.attachments: dict[UUID, list[SupportAttachment]] = {}
        self.message_operations: dict[str, tuple[str, UUID]] = {}

    def add_message(self, message: SupportMessage) -> SupportMessage:
        self.messages.setdefault(message.case_id, []).append(message)
        return message

    def list_messages(self, case_id: UUID) -> Iterable[SupportMessage]:
        return tuple(self.messages.get(case_id, ()))

    def create_or_get_message(
        self,
        message: SupportMessage,
        *,
        request_payload: dict[str, object],
        idempotency_key: str,
    ) -> tuple[SupportMessage, bool]:
        from diddi_support.domain.cases import DomainConflictError, _fingerprint

        fingerprint = _fingerprint(request_payload)
        existing = self.message_operations.get(idempotency_key)
        if existing is not None:
            previous_fingerprint, message_id = existing
            if previous_fingerprint != fingerprint:
                raise DomainConflictError("IDEMPOTENCY_CONFLICT")
            stored = next(
                item
                for messages in self.messages.values()
                for item in messages
                if item.id == message_id
            )
            return stored, False
        self.message_operations[idempotency_key] = (fingerprint, message.id)
        return self.add_message(message), True

    def add_attachment(self, attachment: SupportAttachment) -> SupportAttachment:
        self.attachments.setdefault(attachment.case_id, []).append(attachment)
        return attachment

    def list_attachments(self, case_id: UUID) -> Iterable[SupportAttachment]:
        return tuple(self.attachments.get(case_id, ()))

    def get_attachment(self, attachment_id: UUID) -> SupportAttachment | None:
        return next(
            (
                attachment
                for attachments in self.attachments.values()
                for attachment in attachments
                if attachment.id == attachment_id
            ),
            None,
        )


class PersistentSupportConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PostgresSupportCaseRepository(session)

    async def add_message(
        self,
        message: SupportMessage,
        *,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> SupportMessage:
        return await self.repository.add_message(
            message,
            actor_id=actor_id,
            request_id=request_id,
        )

    async def list_messages(self, case_id: UUID) -> list[SupportMessage]:
        return await self.repository.list_messages(case_id)

    async def create_or_get_message(
        self,
        message: SupportMessage,
        *,
        request_payload: dict[str, object],
        idempotency_key: str,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> tuple[SupportMessage, bool]:
        return await self.repository.create_or_get_message(
            message,
            request_payload=request_payload,
            idempotency_key=idempotency_key,
            actor_id=actor_id,
            request_id=request_id,
        )

    async def add_attachment(
        self,
        attachment: SupportAttachment,
        *,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> SupportAttachment:
        return await self.repository.add_attachment(
            attachment,
            actor_id=actor_id,
            request_id=request_id,
        )

    async def list_attachments(self, case_id: UUID) -> list[SupportAttachment]:
        return await self.repository.list_attachments(case_id)

    async def get_attachment(self, attachment_id: UUID) -> SupportAttachment | None:
        return await self.repository.get_attachment(attachment_id)
