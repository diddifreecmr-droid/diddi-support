from uuid import UUID

import pytest

from diddi_support.domain.cases import (
    CasePriority,
    CaseStatus,
    DomainConflictError,
    InMemorySupportCaseRepository,
    InvalidCaseTransition,
    SupportCase,
    SupportCaseService,
)

RESOURCE_ID = UUID("11111111-1111-1111-1111-111111111111")
REPORTER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _service() -> SupportCaseService:
    return SupportCaseService(InMemorySupportCaseRepository())


def test_case_creation_is_idempotent_and_emits_once() -> None:
    service = _service()
    kwargs = {
        "origin_service": "diddigo",
        "resource_type": "ride",
        "resource_id": RESOURCE_ID,
        "reporter_user_id": REPORTER_ID,
        "category": "safety",
        "subject": "Unsafe ride",
        "idempotency_key": "report-1",
        "priority": CasePriority.HIGH,
    }

    first, created_first = service.open_case(**kwargs)
    second, created_second = service.open_case(**kwargs)

    assert created_first is True
    assert created_second is False
    assert second.id == first.id
    assert len(service.audit_events) == 2
    assert len(service.outbox_events) == 1


def test_reusing_idempotency_key_with_different_payload_is_rejected() -> None:
    service = _service()
    service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=RESOURCE_ID,
        reporter_user_id=REPORTER_ID,
        category="safety",
        subject="Unsafe ride",
        idempotency_key="report-1",
    )

    with pytest.raises(DomainConflictError, match="IDEMPOTENCY_CONFLICT"):
        service.open_case(
            origin_service="diddigo",
            resource_type="ride",
            resource_id=RESOURCE_ID,
            reporter_user_id=REPORTER_ID,
            category="payment",
            subject="Different payload",
            idempotency_key="report-1",
        )


def test_case_transition_rules_are_enforced() -> None:
    case = SupportCase(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=RESOURCE_ID,
        reporter_user_id=REPORTER_ID,
        category="safety",
        subject="Unsafe ride",
    )

    case.transition_to(CaseStatus.IN_PROGRESS)
    case.transition_to(CaseStatus.RESOLVED)
    case.transition_to(CaseStatus.CLOSED)

    with pytest.raises(InvalidCaseTransition):
        case.transition_to(CaseStatus.IN_PROGRESS)
