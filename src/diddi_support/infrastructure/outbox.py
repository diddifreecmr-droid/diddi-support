from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from prometheus_client import CollectorRegistry, Counter, Gauge
from redis.asyncio import Redis
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from diddi_support.core.config import settings
from diddi_support.domain.events import SupportEventType, versioned_event_type
from diddi_support.infrastructure.persistence.models import SupportOutboxEventModel

logger = logging.getLogger("diddi_support.outbox")


class OutboxPermanentError(RuntimeError):
    """Raised when an event cannot be safely published and must be quarantined."""


@dataclass(frozen=True)
class OutboxRecord:
    id: UUID
    event_type: str
    aggregate_id: str
    aggregate_version: int
    payload: dict[str, Any]
    occurred_at: datetime
    attempts: int


class StreamPublisher(Protocol):
    async def publish(self, event: OutboxRecord) -> str: ...


def _safe_payload(event: OutboxRecord) -> dict[str, Any]:
    """Keep the public event payload deliberately smaller than the database payload."""
    event_type = versioned_event_type(event.event_type)
    allowed = {
        SupportEventType.CASE_CREATED.value: {
            "case_id", "origin_service", "resource_type", "resource_id", "priority"
        },
        SupportEventType.CASE_UPDATED.value: {"case_id", "status", "assigned_agent_id"},
        SupportEventType.CASE_ASSIGNED.value: {"case_id", "agent_id", "assigned_agent_id"},
        SupportEventType.CASE_RESOLVED.value: {"case_id", "status", "resolution_code"},
        SupportEventType.CASE_MESSAGE_CREATED.value: {"case_id", "message_id", "visibility"},
    }.get(event_type, {"case_id", "status", "agent_id"})
    return {key: value for key, value in event.payload.items() if key in allowed}


def event_envelope(event: OutboxRecord) -> dict[str, Any]:
    event_type = versioned_event_type(event.event_type)
    return {
        "event_id": str(event.id),
        "event_type": event_type,
        "aggregate_id": str(event.aggregate_id),
        "aggregate_version": event.aggregate_version,
        "occurred_at": event.occurred_at.astimezone(UTC).isoformat(),
        "payload": _safe_payload(event),
    }


class RedisStreamPublisher:
    def __init__(self, client: Redis, *, stream_name: str, maxlen: int) -> None:
        self.client = client
        self.stream_name = stream_name
        self.maxlen = maxlen

    async def publish(self, event: OutboxRecord) -> str:
        envelope = event_envelope(event)
        return await self.client.xadd(
            self.stream_name,
            {"event": json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)},
            maxlen=self.maxlen,
            approximate=True,
        )


class OutboxMetrics:
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()
        self.published = 0
        self.failed = 0
        self.quarantined = 0
        self.pending = 0
        self.oldest_age_seconds = 0.0
        self.published_metric = Counter(
            "diddisupport_outbox_published_total",
            "Outbox events published to Redis",
            registry=self.registry,
        )
        self.failed_metric = Counter(
            "diddisupport_outbox_failed_total",
            "Outbox publish attempts that will be retried",
            registry=self.registry,
        )
        self.quarantined_metric = Counter(
            "diddisupport_outbox_quarantined_total",
            "Outbox events moved to quarantine",
            registry=self.registry,
        )
        self.pending_metric = Gauge(
            "diddisupport_outbox_pending",
            "Unpublished and non-quarantined outbox events",
            registry=self.registry,
        )
        self.oldest_age_metric = Gauge(
            "diddisupport_outbox_oldest_age_seconds",
            "Age of the oldest pending outbox event",
            registry=self.registry,
        )

    def record_pending(self, *, count: int, oldest_created_at: datetime | None) -> None:
        self.pending = count
        self.oldest_age_seconds = (
            max(0.0, (datetime.now(UTC) - oldest_created_at).total_seconds())
            if oldest_created_at
            else 0.0
        )
        self.pending_metric.set(self.pending)
        self.oldest_age_metric.set(self.oldest_age_seconds)

    def snapshot(self) -> dict[str, float | int]:
        return {
            "outbox_pending": self.pending,
            "outbox_published_total": self.published,
            "outbox_failed_total": self.failed,
            "outbox_quarantined_total": self.quarantined,
            "outbox_oldest_age_seconds": self.oldest_age_seconds,
        }


class OutboxDispatcher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: StreamPublisher,
        *,
        worker_id: str | None = None,
        metrics: OutboxMetrics | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.publisher = publisher
        self.worker_id = worker_id or f"{socket.gethostname()}:{id(self)}"
        self.metrics = metrics or OutboxMetrics()

    async def run_once(self) -> int:
        records = await self._claim_batch()
        for record in records:
            if (
                versioned_event_type(record.event_type)
                == SupportEventType.CASE_MESSAGE_CREATED.value
                and record.payload.get("visibility") != "user_visible"
            ):
                await self._mark_failed(
                    record,
                    OutboxPermanentError("internal_note_must_not_be_published"),
                )
                continue
            try:
                await self.publisher.publish(record)
            except Exception as exc:  # noqa: BLE001 - retry policy owns all transport failures
                await self._mark_failed(record, exc)
                continue
            await self._mark_published(record)
        await self._refresh_metrics()
        return len(records)

    async def _claim_batch(self) -> list[OutboxRecord]:
        now = datetime.now(UTC)
        async with self.session_factory() as session:
            statement = (
                select(SupportOutboxEventModel)
                .where(
                    SupportOutboxEventModel.published_at.is_(None),
                    SupportOutboxEventModel.quarantined_at.is_(None),
                    or_(
                        SupportOutboxEventModel.next_attempt_at.is_(None),
                        SupportOutboxEventModel.next_attempt_at <= now,
                    ),
                    or_(
                        SupportOutboxEventModel.lease_until.is_(None),
                        SupportOutboxEventModel.lease_until <= now,
                    ),
                )
                .order_by(SupportOutboxEventModel.created_at)
                .limit(settings.outbox_batch_size)
                .with_for_update(skip_locked=True)
            )
            result = await session.execute(statement)
            rows = list(result.scalars().all())
            lease_until = now + timedelta(seconds=settings.outbox_lease_seconds)
            records: list[OutboxRecord] = []
            for row in rows:
                row.attempts = (row.attempts or 0) + 1
                row.lease_owner = self.worker_id
                row.lease_until = lease_until
                records.append(
                    OutboxRecord(
                        id=row.id,
                        event_type=row.event_type,
                        aggregate_id=row.aggregate_id,
                        aggregate_version=row.aggregate_version or 1,
                        payload=dict(row.payload),
                        occurred_at=row.created_at,
                        attempts=row.attempts,
                    )
                )
            await session.commit()
            return records

    async def _mark_published(self, record: OutboxRecord) -> None:
        async with self.session_factory() as session:
            row = await session.get(SupportOutboxEventModel, record.id)
            if row is None or row.lease_owner != self.worker_id:
                return
            row.published_at = datetime.now(UTC)
            row.lease_owner = None
            row.lease_until = None
            row.last_error = None
            await session.commit()
            self.metrics.published += 1
            self.metrics.published_metric.inc()
            logger.info(
                "outbox_published",
                extra={
                    "event_id": str(record.id),
                    "case_id": record.aggregate_id,
                    "attempt": record.attempts,
                },
            )

    async def _mark_failed(self, record: OutboxRecord, exc: Exception) -> None:
        now = datetime.now(UTC)
        permanent = (
            isinstance(exc, OutboxPermanentError)
            or record.attempts >= settings.outbox_max_attempts
        )
        delay = min(
            settings.outbox_backoff_max_seconds,
            settings.outbox_backoff_base_seconds * (2 ** max(0, record.attempts - 1)),
        )
        async with self.session_factory() as session:
            row = await session.get(SupportOutboxEventModel, record.id)
            if row is None or row.lease_owner != self.worker_id:
                return
            row.last_error = str(exc)[:500]
            row.lease_owner = None
            row.lease_until = None
            if permanent:
                row.quarantined_at = now
                row.next_attempt_at = None
                self.metrics.quarantined += 1
                self.metrics.quarantined_metric.inc()
            else:
                row.next_attempt_at = now + timedelta(seconds=delay)
                self.metrics.failed += 1
                self.metrics.failed_metric.inc()
            await session.commit()
            logger.error(
                "outbox_publish_failed",
                extra={
                    "event_id": str(record.id),
                    "case_id": record.aggregate_id,
                    "attempt": record.attempts,
                    "quarantined": permanent,
                    "error": str(exc),
                },
            )

    async def _refresh_metrics(self) -> None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SupportOutboxEventModel.created_at)
                .where(
                    SupportOutboxEventModel.published_at.is_(None),
                    SupportOutboxEventModel.quarantined_at.is_(None),
                )
                .order_by(SupportOutboxEventModel.created_at)
            )
            created = list(result.scalars().all())
            self.metrics.record_pending(
                count=len(created),
                oldest_created_at=created[0] if created else None,
            )
            logger.info("outbox_metrics", extra=self.metrics.snapshot())
