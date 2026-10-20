from uuid import UUID

from fastapi.testclient import TestClient

from diddi_support.core.auth import (
    BackofficePrincipal,
    ServicePrincipal,
    require_support_agent,
    require_support_service,
)
from diddi_support.main import app
from diddi_support.presentation import internal_router


def test_action_replay_keeps_one_pending_operation_until_provider_confirms() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=UUID("88888888-8888-8888-8888-888888888888"),
        reporter_user_id=UUID("99999999-9999-9999-9999-999999999999"),
        category="payment",
        subject="Refund action",
        idempotency_key="sprint7-action-case",
    )

    def agent() -> BackofficePrincipal:
        return BackofficePrincipal(
            subject="agent-action",
            permissions=frozenset({"diddi-support:read", "diddi-support:write"}),
        )

    def pay() -> ServicePrincipal:
        return ServicePrincipal(
            subject="service:diddipay",
            client_id="diddipay-support",
            scopes=frozenset({"diddi-support:actions:write"}),
        )

    app.dependency_overrides[require_support_agent] = agent
    app.dependency_overrides[require_support_service] = pay
    try:
        client = TestClient(app)
        payload = {
            "case_id": str(case.id),
            "action_type": "diddipay.refund",
            "operation_key": "refund-case-8888",
        }
        first = client.post("/support/v1/backoffice/actions", json=payload)
        replay = client.post("/support/v1/backoffice/actions", json=payload)
        result = client.post(
            f"/support/v1/internal/actions/{first.json()['id']}/result",
            json={"status": "succeeded", "provider_reference": "pay-ref-1"},
        )

        assert first.status_code == 201
        assert replay.status_code == 201
        assert first.json()["id"] == replay.json()["id"]
        assert first.json()["status"] == "pending"
        assert result.status_code == 200
        assert result.json()["status"] == "succeeded"
        assert result.json()["provider_reference"] == "pay-ref-1"
    finally:
        app.dependency_overrides.pop(require_support_agent, None)
        app.dependency_overrides.pop(require_support_service, None)
        internal_router.action_service.actions.clear()
        internal_router.action_service.by_operation_key.clear()
