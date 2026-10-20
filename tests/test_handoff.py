from uuid import UUID

from fastapi.testclient import TestClient

from diddi_support.core.auth import BackofficePrincipal, require_support_agent
from diddi_support.main import app
from diddi_support.presentation import internal_router


def test_human_handoff_stops_ai_competition() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        reporter_user_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        category="support",
        subject="Handoff",
        idempotency_key="sprint9-handoff-case",
    )

    def agent() -> BackofficePrincipal:
        return BackofficePrincipal(
            subject="agent-handoff",
            permissions=frozenset({"diddi-support:reply", "diddi-support:write"}),
        )

    app.dependency_overrides[require_support_agent] = agent
    try:
        client = TestClient(app)
        requested = client.post(
            f"/support/v1/backoffice/cases/{case.id}/handoff",
            json={"mode": "human_requested"},
        )
        active = client.post(
            f"/support/v1/backoffice/cases/{case.id}/handoff",
            json={"mode": "human_active"},
        )
        assert requested.status_code == 200
        assert requested.json()["mode"] == "human_requested"
        assert active.status_code == 200
        assert active.json()["mode"] == "human_active"
        assert internal_router.handoff_service.can_ai_reply(case.id) is False
    finally:
        app.dependency_overrides.pop(require_support_agent, None)
        internal_router.handoff_service.modes.pop(case.id, None)
