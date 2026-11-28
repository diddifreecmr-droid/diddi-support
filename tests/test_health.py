from uuid import UUID

from fastapi.testclient import TestClient

from diddi_support.core.auth import ServicePrincipal, require_support_service
from diddi_support.main import app


def test_liveness() -> None:
    request_id = "health-live-test"
    response = TestClient(app).get("/health/live", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"] == request_id


def test_ping_declares_protocol() -> None:
    response = TestClient(app).get("/support/v1/ping")

    assert response.status_code == 200
    assert response.json() == {
        "module": "diddi-support",
        "protocol": "diddi.module.v1",
        "status": "ok",
    }
    UUID(response.headers["X-Request-ID"])


def test_request_id_is_present_on_health_ready_response() -> None:
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    UUID(response.headers["X-Request-ID"])


def test_request_id_is_present_on_authentication_error() -> None:
    response = TestClient(app).get("/support/v1/backoffice/cases")

    assert response.status_code == 401
    UUID(response.headers["X-Request-ID"])


def test_request_id_is_present_on_forbidden_error() -> None:
    app.dependency_overrides[require_support_service] = lambda: ServicePrincipal(
        subject="service:not-allowed",
        client_id="client-test",
        scopes=frozenset(),
    )
    try:
        response = TestClient(app).get(
            "/support/v1/internal/cases/00000000-0000-0000-0000-000000000000/context"
        )
    finally:
        app.dependency_overrides.pop(require_support_service, None)

    assert response.status_code == 403
    UUID(response.headers["X-Request-ID"])


def test_request_id_is_present_on_not_found_error() -> None:
    response = TestClient(app).get("/missing-route")

    assert response.status_code == 404
    UUID(response.headers["X-Request-ID"])

