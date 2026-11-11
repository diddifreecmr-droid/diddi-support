from datetime import UTC, datetime
from uuid import uuid4

from diddi_support.domain.cases import CasePriority, CaseStatus
from diddi_support.infrastructure.persistence.models import SupportCaseModel
from diddi_support.infrastructure.persistence.repository import _to_domain


def test_persisted_case_status_is_mapped_to_case_status_enum() -> None:
    now = datetime.now(UTC)
    model = SupportCaseModel(
        id=uuid4(),
        origin_service=None,
        resource_type=None,
        resource_id=None,
        origin_report_id="replay-case",
        reporter_user_id=uuid4(),
        category="account_issue",
        subject="Retry an existing case",
        priority=CasePriority.NORMAL.value,
        status=CaseStatus.OPEN.value,
        assigned_agent_id=None,
        resolution_code=None,
        created_at=now,
        updated_at=now,
        resolved_at=None,
        aggregate_version=1,
    )

    case = _to_domain(model)

    assert case.status is CaseStatus.OPEN
    assert case.status.value == "open"
