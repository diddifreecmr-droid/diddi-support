from __future__ import annotations

from enum import StrEnum


class SupportEventType(StrEnum):
    CASE_CREATED = "support.case.created.v1"
    CASE_UPDATED = "support.case.updated.v1"
    CASE_ASSIGNED = "support.case.assigned.v1"
    CASE_MESSAGE_CREATED = "support.case.message.created.v1"
    CASE_RESOLVED = "support.case.resolved.v1"


LEGACY_EVENT_TYPES = {
    "support.case.created": SupportEventType.CASE_CREATED,
    "support.case.updated": SupportEventType.CASE_UPDATED,
    "support.case.status_changed": SupportEventType.CASE_UPDATED,
    "support.case.assigned": SupportEventType.CASE_ASSIGNED,
    "support.case.message.created": SupportEventType.CASE_MESSAGE_CREATED,
}


def versioned_event_type(event_type: str) -> str:
    mapped = LEGACY_EVENT_TYPES.get(event_type)
    if mapped is not None:
        return mapped.value
    if event_type.startswith("support.") and not event_type.endswith(".v1"):
        return f"{event_type}.v1"
    return event_type
