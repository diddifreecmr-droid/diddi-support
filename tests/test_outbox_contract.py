import json
from datetime import UTC, datetime
from uuid import UUID

import pytest

from diddi_support.domain.events import SupportEventType, versioned_event_type
from diddi_support.infrastructure.outbox import (
    OutboxMetrics,
    OutboxRecord,
    RedisStreamPublisher,
    event_envelope,
)

CASE_ID = UUID("11111111-1111-1111-1111-111111111111")
MESSAGE_ID = UUID("22222222-2222-2222-2222-222222222222")
EVENT_ID = UUID("33333333-3333-3333-3333-333333333333")


def _message_event(*, version: int = 4, visibility: str = "user_visible") -> OutboxRecord:
    return OutboxRecord(
        id=EVENT_ID,
        event_type="support.case.message.created",
        aggregate_id=str(CASE_ID),
        aggregate_version=version,
        payload={
            "case_id": str(CASE_ID),
            "message_id": str(MESSAGE_ID),
            "visibility": visibility,
            "body": "ne doit jamais sortir",
            "author_id": "private-user-id",
        },
        occurred_at=datetime(2026, 10, 21, tzinfo=UTC),
        attempts=1,
    )


def test_message_event_is_versioned_and_redacts_body_and_sensitive_fields() -> None:
    envelope = event_envelope(_message_event())

    assert envelope == {
        "event_id": str(EVENT_ID),
        "event_type": SupportEventType.CASE_MESSAGE_CREATED.value,
        "aggregate_id": str(CASE_ID),
        "aggregate_version": 4,
        "occurred_at": "2026-10-21T00:00:00+00:00",
        "payload": {
            "case_id": str(CASE_ID),
            "message_id": str(MESSAGE_ID),
            "visibility": "user_visible",
        },
    }
    assert "body" not in json.dumps(envelope)
    assert "author_id" not in json.dumps(envelope)


def test_internal_note_is_not_a_user_notification_payload() -> None:
    envelope = event_envelope(_message_event(visibility="internal_note"))

    assert envelope["payload"]["visibility"] == "internal_note"
    assert "body" not in json.dumps(envelope)


def test_legacy_event_names_are_mapped_to_versioned_contract() -> None:
    assert versioned_event_type("support.case.updated") == "support.case.updated.v1"
    assert versioned_event_type("support.case.assigned") == "support.case.assigned.v1"
    assert versioned_event_type("support.case.status_changed") == "support.case.updated.v1"


@pytest.mark.asyncio
async def test_redis_publisher_uses_diddisupport_stream_and_bounded_retention() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.calls = []

        async def xadd(self, stream, fields, *, maxlen, approximate):
            self.calls.append((stream, fields, maxlen, approximate))
            return "1730000000000-0"

    redis = FakeRedis()
    stream = RedisStreamPublisher(redis, stream_name="diddisupport.events", maxlen=100_000)

    result = await stream.publish(_message_event())

    assert result == "1730000000000-0"
    assert redis.calls[0][0] == "diddisupport.events"
    assert redis.calls[0][2:] == (100_000, True)
    assert json.loads(redis.calls[0][1]["event"])["event_id"] == str(EVENT_ID)


def test_outbox_metrics_expose_required_operational_values() -> None:
    metrics = OutboxMetrics()
    metrics.record_pending(count=3, oldest_created_at=datetime.now(UTC))

    assert metrics.snapshot()["outbox_pending"] == 3
    assert "outbox_oldest_age_seconds" in metrics.snapshot()
