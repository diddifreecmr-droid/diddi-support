from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid4


class CaseStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    WAITING_INTERNAL = "waiting_internal"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageVisibility(StrEnum):
    USER_VISIBLE = "user_visible"
    INTERNAL_NOTE = "internal_note"
    SYSTEM_EVENT = "system_event"


class DomainConflictError(ValueError):
    """Raised when an idempotency key is reused with another payload."""


class InvalidCaseTransition(ValueError):
    """Raised when a case status transition is not allowed."""


ALLOWED_TRANSITIONS: dict[CaseStatus, frozenset[CaseStatus]] = {
    CaseStatus.OPEN: frozenset(
        {CaseStatus.IN_PROGRESS, CaseStatus.WAITING_USER, CaseStatus.WAITING_INTERNAL}
    ),
    CaseStatus.IN_PROGRESS: frozenset(
        {CaseStatus.WAITING_USER, CaseStatus.WAITING_INTERNAL, CaseStatus.RESOLVED}
    ),
    CaseStatus.WAITING_USER: frozenset({CaseStatus.IN_PROGRESS, CaseStatus.RESOLVED}),
    CaseStatus.WAITING_INTERNAL: frozenset({CaseStatus.IN_PROGRESS, CaseStatus.RESOLVED}),
    CaseStatus.RESOLVED: frozenset({CaseStatus.CLOSED, CaseStatus.IN_PROGRESS}),
    CaseStatus.CLOSED: frozenset(),
}


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class SupportCase:
    origin_service: str
    resource_type: str
    resource_id: UUID
    reporter_user_id: UUID
    category: str
    subject: str
    priority: CasePriority = CasePriority.NORMAL
    origin_report_id: str | None = None
    id: UUID = field(default_factory=uuid4)
    status: CaseStatus = CaseStatus.OPEN
    assigned_agent_id: UUID | None = None
    resolution_code: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None

    def transition_to(self, status: CaseStatus, *, now: datetime | None = None) -> None:
        if status == self.status:
            return
        if status not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidCaseTransition(f"{self.status} -> {status} is not allowed")
        current_time = now or utc_now()
        self.status = status
        self.updated_at = current_time
        if status == CaseStatus.RESOLVED:
            self.resolved_at = current_time
        elif self.resolved_at is not None and status == CaseStatus.IN_PROGRESS:
            self.resolved_at = None

    def assign(self, agent_id: UUID, *, now: datetime | None = None) -> None:
        self.assigned_agent_id = agent_id
        self.updated_at = now or utc_now()

    def change_priority(self, priority: CasePriority, *, now: datetime | None = None) -> None:
        self.priority = priority
        self.updated_at = now or utc_now()


@dataclass(frozen=True)
class AuditEvent:
    action: str
    target_type: str
    target_id: str
    outcome: str
    actor_id: UUID | None
    request_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class OutboxEvent:
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
    correlation_id: str | None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


class SupportCaseRepository(Protocol):
    def create_or_get(
        self,
        case: SupportCase,
        *,
        request_payload: dict[str, Any],
        idempotency_key: str,
    ) -> tuple[SupportCase, bool]:
        """Return the existing case or create it exactly once."""


class InMemorySupportCaseRepository:
    def __init__(self) -> None:
        self._cases: dict[UUID, SupportCase] = {}
        self._operations: dict[str, tuple[str, UUID]] = {}

    def create_or_get(
        self,
        case: SupportCase,
        *,
        request_payload: dict[str, Any],
        idempotency_key: str,
    ) -> tuple[SupportCase, bool]:
        fingerprint = _fingerprint(request_payload)
        existing = self._operations.get(idempotency_key)
        if existing is not None:
            previous_fingerprint, case_id = existing
            if previous_fingerprint != fingerprint:
                raise DomainConflictError("IDEMPOTENCY_CONFLICT")
            return self._cases[case_id], False
        self._operations[idempotency_key] = (fingerprint, case.id)
        self._cases[case.id] = case
        return case, True

    def get(self, case_id: UUID) -> SupportCase | None:
        return self._cases.get(case_id)

    def list(
        self,
        *,
        status: CaseStatus | None = None,
        priority: CasePriority | None = None,
        limit: int = 50,
    ) -> list[SupportCase]:
        cases = [
            case
            for case in self._cases.values()
            if (status is None or case.status == status)
            and (priority is None or case.priority == priority)
        ]
        return sorted(cases, key=lambda case: case.created_at)[:limit]


class SupportCaseService:
    def __init__(self, repository: SupportCaseRepository) -> None:
        self.repository = repository
        self.audit_events: list[AuditEvent] = []
        self.outbox_events: list[OutboxEvent] = []

    def open_case(
        self,
        *,
        origin_service: str,
        resource_type: str,
        resource_id: UUID,
        reporter_user_id: UUID,
        category: str,
        subject: str,
        idempotency_key: str,
        origin_report_id: str | None = None,
        priority: CasePriority = CasePriority.NORMAL,
        request_id: str | None = None,
    ) -> tuple[SupportCase, bool]:
        payload = {
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
        result, created = self.repository.create_or_get(
            case,
            request_payload=payload,
            idempotency_key=idempotency_key,
        )
        self.audit_events.append(
            AuditEvent(
                action="support.case.created" if created else "support.case.reused",
                target_type="support_case",
                target_id=str(result.id),
                outcome="succeeded",
                actor_id=reporter_user_id,
                request_id=request_id,
                metadata={"origin_service": origin_service, "resource_type": resource_type},
            )
        )
        if created:
            self.outbox_events.append(
                OutboxEvent(
                    event_type="support.case.created",
                    aggregate_type="support_case",
                    aggregate_id=str(result.id),
                    correlation_id=request_id,
                    payload={
                        "origin_service": origin_service,
                        "resource_type": resource_type,
                        "resource_id": str(resource_id),
                        "priority": priority.value,
                    },
                )
            )
        return result, created

    def assign_case(
        self,
        case_id: UUID,
        agent_id: UUID,
        *,
        actor_id: str,
        request_id: str | None,
    ) -> SupportCase | None:
        case = self.repository.get(case_id)
        if case is None:
            return None
        case.assign(agent_id)
        self.audit_events.append(
            AuditEvent(
                action="support.case.assigned",
                target_type="support_case",
                target_id=str(case.id),
                outcome="succeeded",
                actor_id=None,
                request_id=request_id,
                metadata={"agent_id": str(agent_id), "actor_id": actor_id},
            )
        )
        self.outbox_events.append(
            OutboxEvent(
                event_type="support.case.assigned",
                aggregate_type="support_case",
                aggregate_id=str(case.id),
                correlation_id=request_id,
                payload={"agent_id": str(agent_id)},
            )
        )
        return case

    def transition_case(
        self,
        case_id: UUID,
        new_status: CaseStatus,
        *,
        actor_id: str,
        request_id: str | None,
    ) -> SupportCase | None:
        case = self.repository.get(case_id)
        if case is None:
            return None
        case.transition_to(new_status)
        self.audit_events.append(
            AuditEvent(
                action="support.case.status_changed",
                target_type="support_case",
                target_id=str(case.id),
                outcome="succeeded",
                actor_id=None,
                request_id=request_id,
                metadata={"status": new_status.value, "actor_id": actor_id},
            )
        )
        self.outbox_events.append(
            OutboxEvent(
                event_type="support.case.updated",
                aggregate_type="support_case",
                aggregate_id=str(case.id),
                correlation_id=request_id,
                payload={"status": new_status.value},
            )
        )
        return case


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
