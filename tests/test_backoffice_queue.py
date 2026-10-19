from uuid import UUID

from fastapi.testclient import TestClient

from diddi_support.core.auth import BackofficePrincipal, require_support_agent
from diddi_support.main import app
from diddi_support.presentation import internal_router

CASE_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
RIDE_ID = UUID("33333333-3333-3333-3333-333333333333")
AGENT_ID = UUID("44444444-4444-4444-4444-444444444444")


def test_backoffice_queue_assigns_and_transitions_case() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=RIDE_ID,
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="Queue test",
        idempotency_key="queue-case-1",
    )
    app.dependency_overrides[require_support_agent] = lambda: BackofficePrincipal(
        subject="agent-supervisor",
        permissions=frozenset(
            {"diddi-support:read", "diddi-support:assign", "diddi-support:write"}
        ),
    )
    try:
        client = TestClient(app)
        queue = client.get("/support/v1/backoffice/cases?status=open&limit=10")
        assert queue.status_code == 200
        assert any(item["id"] == str(case.id) for item in queue.json())

        assigned = client.post(
            f"/support/v1/backoffice/cases/{case.id}/assign",
            json={"agent_id": str(AGENT_ID)},
        )
        assert assigned.status_code == 200
        assert assigned.json()["assigned_agent_id"] == str(AGENT_ID)

        transitioned = client.post(
            f"/support/v1/backoffice/cases/{case.id}/transition",
            json={"status": "in_progress"},
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "in_progress"
    finally:
        app.dependency_overrides.pop(require_support_agent, None)


def test_backoffice_queue_rejects_invalid_transition() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=RIDE_ID,
        reporter_user_id=CASE_USER_ID,
        category="support",
        subject="Invalid transition test",
        idempotency_key="queue-case-2",
    )
    app.dependency_overrides[require_support_agent] = lambda: BackofficePrincipal(
        subject="agent-supervisor",
        permissions=frozenset({"diddi-support:write"}),
    )
    try:
        response = TestClient(app).post(
            f"/support/v1/backoffice/cases/{case.id}/transition",
            json={"status": "closed"},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "INVALID_CASE_TRANSITION"
    finally:
        app.dependency_overrides.pop(require_support_agent, None)
