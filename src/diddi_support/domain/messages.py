from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class MessageAuthorType(StrEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class AttachmentPurpose(StrEnum):
    PHOTO = "diddisupport_case_photo"
    VOICE = "diddisupport_case_voice"
    DOCUMENT = "diddisupport_case_document"


ALLOWED_ATTACHMENT_MIME_TYPES: dict[AttachmentPurpose, frozenset[str]] = {
    AttachmentPurpose.PHOTO: frozenset({"image/jpeg", "image/png", "image/webp"}),
    AttachmentPurpose.VOICE: frozenset({"audio/mpeg", "audio/ogg", "audio/wav", "audio/webm"}),
    AttachmentPurpose.DOCUMENT: frozenset({"application/pdf", "text/plain"}),
}


@dataclass(frozen=True)
class SupportMessage:
    case_id: UUID
    author_type: MessageAuthorType
    author_id: str
    body: str
    visibility: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class SupportAttachment:
    case_id: UUID
    file_id: UUID
    owner_user_id: UUID
    purpose: AttachmentPurpose
    mime_type: str
    size_bytes: int
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
