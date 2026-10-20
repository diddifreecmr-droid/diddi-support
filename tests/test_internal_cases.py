from fastapi.testclient import TestClient

from diddi_support.core.auth import ServicePrincipal, require_support_service
from diddi_support.main import app

RIDE_ID = "11111111-1111-1111-1111-111111111111"
REPORTER_ID = "22222222-2222-2222-2222-222222222222"


def _principal() -> ServicePrincipal:
    return ServicePrincipal(
        subject="service:diddigo",
        client_id="diddigo-staging-support",
        scopes=frozenset({"diddi-support:cases:create"}),
    )


def test_diddigo_can_create_and_replay_a_case() -> None:
    app.dependency_overrides[require_support_service] = _principal
    try:
        client = TestClient(app)
        payload = {
            "origin_service": "diddigo",
            "resource_type": "ride",
            "resource_id": RIDE_ID,
            "origin_report_id": "ride-report-1",
            "reporter_user_id": REPORTER_ID,
            "category": "safety",
            "subject": "Unsafe ride",
            "priority": "high",
        }
        headers = {"Idempotency-Key": "support-report-1", "X-Request-ID": "req-1"}

        first = client.post("/support/v1/internal/cases", json=payload, headers=headers)
        replay = client.post("/support/v1/internal/cases", json=payload, headers=headers)

        assert first.status_code == 201
        assert replay.status_code == 201
        assert first.json()["id"] == replay.json()["id"]
        assert first.json()["created"] is True
        assert replay.json()["created"] is False
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_service_cannot_create_for_another_origin() -> None:
    app.dependency_overrides[require_support_service] = _principal
    try:
        response = TestClient(app).post(
            "/support/v1/internal/cases",
            json={
                "origin_service": "diddifood",
                "resource_type": "order",
                "resource_id": RIDE_ID,
                "reporter_user_id": REPORTER_ID,
                "category": "order",
                "subject": "Wrong origin",
            },
            headers={"Idempotency-Key": "support-report-2"},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "SERVICE_ORIGIN_FORBIDDEN"
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_service_without_scope_is_rejected() -> None:
    app.dependency_overrides[require_support_service] = lambda: ServicePrincipal(
        subject="service:diddigo",
        client_id="diddigo-staging-support",
        scopes=frozenset(),
    )
    try:
        response = TestClient(app).post(
            "/support/v1/internal/cases",
            json={
                "origin_service": "diddigo",
                "resource_type": "ride",
                "resource_id": RIDE_ID,
                "reporter_user_id": REPORTER_ID,
                "category": "safety",
                "subject": "Missing scope",
            },
            headers={"Idempotency-Key": "support-report-3"},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "SERVICE_SCOPE_FORBIDDEN"
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_diddicomms_can_create_for_a_delegated_business_origin() -> None:
    app.dependency_overrides[require_support_service] = lambda: ServicePrincipal(
        subject="service:diddicomms",
        client_id="diddicomms-support",
        scopes=frozenset({"diddi-support:cases:create"}),
    )
    try:
        response = TestClient(app).post(
            "/support/v1/internal/cases",
            json={
                "origin_service": "diddisend",
                "resource_type": "delivery",
                "resource_id": RIDE_ID,
                "reporter_user_id": REPORTER_ID,
                "category": "delivery_issue",
                "subject": "Delivery is late",
            },
            headers={"Idempotency-Key": "comms-delegated-1"},
        )
        assert response.status_code == 201
        assert response.json()["origin_service"] == "diddisend"
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_diddicomms_cannot_create_for_an_unregistered_origin() -> None:
    app.dependency_overrides[require_support_service] = lambda: ServicePrincipal(
        subject="service:diddicomms",
        client_id="diddicomms-support",
        scopes=frozenset({"diddi-support:cases:create"}),
    )
    try:
        response = TestClient(app).post(
            "/support/v1/internal/cases",
            json={
                "origin_service": "unknown-module",
                "resource_type": "resource",
                "resource_id": RIDE_ID,
                "reporter_user_id": REPORTER_ID,
                "category": "other",
                "subject": "Unknown origin",
            },
            headers={"Idempotency-Key": "comms-delegated-2"},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "SERVICE_ORIGIN_FORBIDDEN"
    finally:
        app.dependency_overrides.pop(require_support_service, None)
