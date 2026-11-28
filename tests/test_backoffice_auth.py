from uuid import UUID

import jwt
import pytest
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


def _request() -> Request:
    return Request({"type": "http", "headers": []})


def _token(token_type: str) -> str:
    return jwt.encode({"token_type": token_type}, key="", algorithm="none")


def test_service_token_is_converted_to_delegated_backoffice_principal(monkeypatch) -> None:
    monkeypatch.setattr(settings, "backoffice_service_client_ids", "diddiadmin-client")
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
        client_id="diddiadmin-client",
        actor=actor,
        reason="Review case",
    )

    assert principal == BackofficePrincipal(
        subject=actor,
        permissions=frozenset({"diddi-support:read", "diddi-support:write"}),
        service_subject="service:diddiadmin",
        client_id="diddiadmin-client",
        reason="Review case",
    )
    assert UUID(principal.subject)


def test_service_token_requires_global_client_allowlist(monkeypatch) -> None:
    monkeypatch.setattr(settings, "backoffice_service_client_ids", "another-client")

    with pytest.raises(ServiceAuthenticationError, match="BACKOFFICE_CLIENT_ID_FORBIDDEN"):
        require_support_agent(
            _request(),
            authorization=f"Bearer {_token('service')}",
            client_id="diddiadmin-client",
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
