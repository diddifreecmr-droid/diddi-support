from fastapi.testclient import TestClient

from diddi_support.main import app


def test_liveness() -> None:
    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ping_declares_protocol() -> None:
    response = TestClient(app).get("/support/v1/ping")

    assert response.status_code == 200
    assert response.json() == {
        "module": "diddi-support",
        "protocol": "diddi.module.v1",
        "status": "ok",
    }

