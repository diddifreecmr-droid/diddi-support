from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class SosNotificationStatus(StrEnum):
    RECORDED = "recorded"
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class SosHandlingStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class SosAlert:
    reporter_user_id: UUID
    origin_service: str
    location_latitude: float | None = None
    location_longitude: float | None = None
    case_id: UUID | None = None
    source_alert_id: str | None = None
    source_notification_sent: bool = False
    id: UUID = field(default_factory=uuid4)
    notification_status: SosNotificationStatus = SosNotificationStatus.RECORDED
    handling_status: SosHandlingStatus = SosHandlingStatus.UNCONFIRMED
    notification_attempts: int = 0
    escalation_level: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.source_notification_sent:
            self.notification_status = SosNotificationStatus.SENT
        elif self.notification_status == SosNotificationStatus.RECORDED:
            self.notification_status = SosNotificationStatus.PENDING

    def confirm(self, *, now: datetime | None = None) -> None:
        if self.handling_status == SosHandlingStatus.UNCONFIRMED:
            self.handling_status = SosHandlingStatus.CONFIRMED
        self.updated_at = now or datetime.now(UTC)

    def start(self, *, now: datetime | None = None) -> None:
        if self.handling_status not in {
            SosHandlingStatus.CONFIRMED,
            SosHandlingStatus.IN_PROGRESS,
        }:
            raise ValueError("SOS must be confirmed before work starts")
        self.handling_status = SosHandlingStatus.IN_PROGRESS
        self.updated_at = now or datetime.now(UTC)

    def complete(self, *, now: datetime | None = None) -> None:
        if self.handling_status not in {
            SosHandlingStatus.CONFIRMED,
            SosHandlingStatus.IN_PROGRESS,
        }:
            raise ValueError("SOS must be confirmed before completion")
        self.handling_status = SosHandlingStatus.COMPLETED
        self.updated_at = now or datetime.now(UTC)

    def retry_notification(self, *, max_attempts: int, now: datetime | None = None) -> None:
        self.notification_attempts += 1
        self.updated_at = now or datetime.now(UTC)
        if self.notification_attempts >= max_attempts:
            self.notification_status = SosNotificationStatus.FAILED
            self.escalation_level = max(self.escalation_level, 1)
        else:
            self.notification_status = SosNotificationStatus.PENDING
