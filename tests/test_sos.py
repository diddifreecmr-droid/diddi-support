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

REPORTER_ID = UUID("77777777-7777-7777-7777-777777777777")


def test_diddigo_sos_is_idempotent_and_does_not_double_notify() -> None:
    app.dependency_overrides[require_support_service] = lambda: ServicePrincipal(
        subject="service:diddigo",
        client_id="diddigo-support",
        scopes=frozenset({"diddi-support:sos:create"}),
    )
    try:
        client = TestClient(app)
        payload = {
            "reporter_user_id": str(REPORTER_ID),
            "origin_service": "diddigo",
            "source_alert_id": "diddigo-sos-unique-1",
            "source_notification_sent": True,
        }
        first = client.post("/support/v1/internal/sos", json=payload)
        replay = client.post("/support/v1/internal/sos", json=payload)

        assert first.status_code == 201
        assert replay.status_code == 201
        assert first.json()["id"] == replay.json()["id"]
        assert first.json()["notification_status"] == "sent"
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_sos_requires_explicit_agent_confirmation() -> None:
    def service_principal() -> ServicePrincipal:
        return ServicePrincipal(
            subject="service:diddigo",
            client_id="diddigo-support",
            scopes=frozenset({"diddi-support:sos:create"}),
        )

    def agent_principal() -> BackofficePrincipal:
        return BackofficePrincipal(
            subject="agent-sos",
            permissions=frozenset({"diddi-support:read", "diddi-support:sos-operate"}),
        )
    app.dependency_overrides[require_support_service] = service_principal
    app.dependency_overrides[require_support_agent] = agent_principal
    try:
        client = TestClient(app)
        created = client.post(
            "/support/v1/internal/sos",
            json={
                "reporter_user_id": str(REPORTER_ID),
                "origin_service": "diddigo",
                "source_alert_id": "diddigo-sos-unique-2",
            },
        )
        alert_id = created.json()["id"]
        not_confirmed = client.post(f"/support/v1/backoffice/sos/{alert_id}/start")
        confirmed = client.post(f"/support/v1/backoffice/sos/{alert_id}/confirm")
        started = client.post(f"/support/v1/backoffice/sos/{alert_id}/start")

        assert created.status_code == 201
        assert not_confirmed.status_code == 409
        assert not_confirmed.json()["detail"]["code"] == "SOS_CONFIRMATION_REQUIRED"
        assert confirmed.status_code == 200
        assert confirmed.json()["handling_status"] == "confirmed"
        assert started.status_code == 200
        assert started.json()["handling_status"] == "in_progress"
    finally:
        app.dependency_overrides.pop(require_support_service, None)
        app.dependency_overrides.pop(require_support_agent, None)
        internal_router.sos_service.alerts.clear()
        internal_router.sos_service.by_source_alert.clear()
