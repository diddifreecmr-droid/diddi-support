from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ActionStatus(StrEnum):
    REQUESTED = "requested"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ActionType(StrEnum):
    DIDDIGO_CANCEL = "diddigo.cancel"
    DIDDIPAY_REFUND = "diddipay.refund"


@dataclass
class SupportAction:
    case_id: UUID
    operation_key: str
    action_type: ActionType
    requested_by: str
    id: UUID = field(default_factory=uuid4)
    status: ActionStatus = ActionStatus.REQUESTED
    provider_reference: str | None = None
    result_code: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark_pending(self) -> None:
        self.status = ActionStatus.PENDING
        self.updated_at = datetime.now(UTC)

    def confirm(self, *, provider_reference: str) -> None:
        self.status = ActionStatus.SUCCEEDED
        self.provider_reference = provider_reference
        self.result_code = None
        self.updated_at = datetime.now(UTC)

    def fail(self, *, result_code: str, unknown: bool = False) -> None:
        self.status = ActionStatus.UNKNOWN if unknown else ActionStatus.FAILED
        self.result_code = result_code
        self.updated_at = datetime.now(UTC)
