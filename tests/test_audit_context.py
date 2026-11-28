from contextvars import copy_context

from diddi_support.core.audit_context import reset_backoffice_reason, set_backoffice_reason
from diddi_support.infrastructure.persistence.repository import _audit_metadata


def test_backoffice_reason_is_added_to_persistent_audit_metadata() -> None:
    token = set_backoffice_reason("Review case")
    try:
        assert _audit_metadata({"actor_id": "agent-1"}) == {
            "actor_id": "agent-1",
            "backoffice_reason": "Review case",
        }
    finally:
        reset_backoffice_reason(token)


def test_missing_backoffice_reason_does_not_change_audit_metadata() -> None:
    assert _audit_metadata({"actor_id": "agent-1"}) == {"actor_id": "agent-1"}


def test_reset_from_a_different_context_does_not_break_request_cleanup() -> None:
    token = copy_context().run(set_backoffice_reason, "Review case")

    reset_backoffice_reason(token)
