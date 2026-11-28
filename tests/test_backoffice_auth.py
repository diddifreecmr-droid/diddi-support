from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from diddi_support.core.auth import (
    BackofficePrincipal,
    BackofficeTokenVerifier,
    ServiceAuthenticationError,
    ServicePrincipal,
    ServiceTokenVerifier,
    require_support_agent,
)
from diddi_support.core.config import settings
from diddi_support.main import app


def _request() -> Request:
    return Request({"type": "http", "headers": []})


def _token(token_type: str) -> str:
    return jwt.encode({"token_type": token_type}, key="", algorithm="none")


def test_service_token_is_converted_to_delegated_backoffice_principal(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "backoffice_service_client_ids",
        "backoffice-staging-diddisupport",
    )
    monkeypatch.setattr(
        ServiceTokenVerifier,
        "verify",
        lambda self, token, client_id: ServicePrincipal(
            subject="service:diddiadmin",
            client_id=client_id,
            scopes=frozenset({"diddi-support:read", "diddi-support:write"}),
        ),
    )

    actor = "11111111-1111-4111-8111-111111111111"
    principal = require_support_agent(
        _request(),
        authorization=f"Bearer {_token('service')}",
        client_id="backoffice-staging-diddisupport",
        actor=actor,
        reason="Review case",
    )

    assert principal == BackofficePrincipal(
        subject=actor,
        permissions=frozenset({"diddi-support:read", "diddi-support:write"}),
        service_subject="service:diddiadmin",
        client_id="backoffice-staging-diddisupport",
        reason="Review case",
    )
    assert UUID(principal.subject)


def test_service_token_requires_global_client_allowlist(monkeypatch) -> None:
    monkeypatch.setattr(settings, "backoffice_service_client_ids", "another-client")

    with pytest.raises(ServiceAuthenticationError, match="BACKOFFICE_CLIENT_ID_FORBIDDEN"):
        require_support_agent(
            _request(),
            authorization=f"Bearer {_token('service')}",
            client_id="backoffice-staging-diddisupport",
            actor="11111111-1111-4111-8111-111111111111",
        )


def test_user_token_path_remains_compatible(monkeypatch) -> None:
    monkeypatch.setattr(
        BackofficeTokenVerifier,
        "verify",
        lambda self, token: BackofficePrincipal(
            subject="agent-1",
            permissions=frozenset({"diddi-support:read"}),
        ),
    )

    principal = require_support_agent(
        _request(),
        authorization=f"Bearer {_token('user')}",
    )

    assert principal.subject == "agent-1"
    assert principal.permissions == frozenset({"diddi-support:read"})


def test_delegated_service_principal_uses_route_scopes() -> None:
    actor = "11111111-1111-4111-8111-111111111111"
    app.dependency_overrides[require_support_agent] = lambda: BackofficePrincipal(
        subject=actor,
        permissions=frozenset({"diddi-support:read"}),
        service_subject="service:diddiadmin",
        client_id="backoffice-staging-diddisupport",
    )
    try:
        response = TestClient(app).get("/support/v1/backoffice/cases")
    finally:
        app.dependency_overrides.pop(require_support_agent, None)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
