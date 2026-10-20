from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from diddi_support.application.context import (
    BusinessContext,
    ContextNotFoundError,
    ContextProviderUnavailableError,
    ContextService,
)
from diddi_support.core.auth import (
    BackofficePrincipal,
    ServicePrincipal,
    require_support_agent,
    require_support_service,
)
from diddi_support.infrastructure.context.http import HttpContextProvider
from diddi_support.main import app
from diddi_support.presentation import internal_router

RIDE_ID = UUID("11111111-1111-1111-1111-111111111111")


def _transport(payload: object, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/internal/v1/support/ride/{RIDE_ID}/context"
        assert request.headers["X-Support-Context-Scope"] == "diddigo:support-context:read"
        return httpx.Response(status_code, json=payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_http_context_provider_reads_standardized_context() -> None:
    provider = HttpContextProvider(
        base_url="http://diddigo",
        scope="diddigo:support-context:read",
        transport=_transport(
            {
                "protocol": "diddi.context.v1",
                "origin_service": "diddigo",
                "resource_type": "ride",
                "resource_id": str(RIDE_ID),
                "data": {"status": "completed", "fare": {"amount": 2500, "currency": "XAF"}},
                "redacted_fields": ["driver.phone"],
                "as_of": "2026-10-20T11:00:00Z",
            }
        ),
    )

    context = await provider.fetch(resource_type="ride", resource_id=RIDE_ID, request_id="req-1")

    assert context.data["status"] == "completed"
    assert context.redacted_fields == ["driver.phone"]
    assert context.as_of is not None
    assert context.fetched_at is not None


@pytest.mark.asyncio
async def test_context_provider_maps_not_found() -> None:
    provider = HttpContextProvider(
        base_url="http://diddigo",
        scope="diddigo:support-context:read",
        transport=_transport({}, status_code=404),
    )

    with pytest.raises(ContextNotFoundError):
        await provider.fetch(resource_type="ride", resource_id=RIDE_ID, request_id=None)


@pytest.mark.asyncio
async def test_context_service_rejects_mismatched_resource() -> None:
    class FakeProvider:
        async def fetch(self, **_: object) -> BusinessContext:
            return BusinessContext(
                protocol="diddi.context.v1",
                origin_service="diddigo",
                resource_type="order",
                resource_id=RIDE_ID,
                data={},
            )

    with pytest.raises(ContextProviderUnavailableError, match="CONTEXT_RESOURCE_MISMATCH"):
        await ContextService({"diddigo": FakeProvider()}).get_context(
            origin_service="diddigo",
            resource_type="ride",
            resource_id=RIDE_ID,
            request_id=None,
        )


def test_internal_context_endpoint_returns_owner_context() -> None:
    class FakeProvider:
        async def fetch(self, **_: object) -> BusinessContext:
            return BusinessContext(
                protocol="diddi.context.v1",
                origin_service="diddigo",
                resource_type="ride",
                resource_id=RIDE_ID,
                data={"status": "completed"},
            )

    original_service = internal_router.context_service
    internal_router.context_service = ContextService({"diddigo": FakeProvider()})
    app.dependency_overrides[require_support_service] = lambda: ServicePrincipal(
        subject="service:diddicomms",
        client_id="diddicomms-support",
        scopes=frozenset({"diddi-support:cases:read"}),
    )
    try:
        response = TestClient(app).get(
            f"/support/v1/internal/context/diddigo/ride/{RIDE_ID}",
            headers={"X-Request-ID": "req-context-1"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "completed"
    finally:
        internal_router.context_service = original_service
        app.dependency_overrides.pop(require_support_service, None)


def test_internal_context_endpoint_requires_read_scope() -> None:
    app.dependency_overrides[require_support_service] = lambda: ServicePrincipal(
        subject="service:diddicomms",
        client_id="diddicomms-support",
        scopes=frozenset(),
    )
    try:
        response = TestClient(app).get(
            f"/support/v1/internal/context/diddigo/ride/{RIDE_ID}",
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "SERVICE_SCOPE_FORBIDDEN"
    finally:
        app.dependency_overrides.pop(require_support_service, None)


def test_case_context_endpoint_resolves_case_reference() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=RIDE_ID,
        reporter_user_id=UUID("22222222-2222-2222-2222-222222222222"),
        category="safety",
        subject="Unsafe ride",
        idempotency_key="context-case-1",
    )

    class FakeProvider:
        async def fetch(self, **_: object) -> BusinessContext:
            return BusinessContext(
                protocol="diddi.context.v1",
                origin_service="diddigo",
                resource_type="ride",
                resource_id=RIDE_ID,
                data={"status": "completed", "driver": {"id": "driver-1"}},
            )

    original_service = internal_router.context_service
    internal_router.context_service = ContextService({"diddigo": FakeProvider()})
    app.dependency_overrides[require_support_service] = lambda: ServicePrincipal(
        subject="service:diddicomms",
        client_id="diddicomms-support",
        scopes=frozenset({"diddi-support:cases:read"}),
    )
    try:
        response = TestClient(app).get(f"/support/v1/internal/cases/{case.id}/context")
        assert response.status_code == 200
        assert response.json()["case"]["id"] == str(case.id)
        assert response.json()["context"]["data"]["status"] == "completed"
    finally:
        internal_router.context_service = original_service
        app.dependency_overrides.pop(require_support_service, None)


def test_backoffice_context_endpoint_enforces_agent_permission() -> None:
    case, _ = internal_router.case_service.open_case(
        origin_service="diddigo",
        resource_type="ride",
        resource_id=RIDE_ID,
        reporter_user_id=UUID("22222222-2222-2222-2222-222222222222"),
        category="safety",
        subject="Backoffice context",
        idempotency_key="context-case-backoffice-1",
    )

    class FakeProvider:
        async def fetch(self, **_: object) -> BusinessContext:
            return BusinessContext(
                protocol="diddi.context.v1",
                origin_service="diddigo",
                resource_type="ride",
                resource_id=RIDE_ID,
                data={"status": "in_progress"},
            )

    original_service = internal_router.context_service
    internal_router.context_service = ContextService({"diddigo": FakeProvider()})
    app.dependency_overrides[require_support_agent] = lambda: BackofficePrincipal(
        subject="agent-1",
        permissions=frozenset({"diddi-support:read"}),
    )
    try:
        response = TestClient(app).get(
            f"/support/v1/backoffice/cases/{case.id}/context",
            headers={"X-Request-ID": "req-agent-1"},
        )
        assert response.status_code == 200
        assert response.json()["context"]["data"]["status"] == "in_progress"
    finally:
        internal_router.context_service = original_service
        app.dependency_overrides.pop(require_support_agent, None)


def test_backoffice_context_endpoint_rejects_missing_permission() -> None:
    app.dependency_overrides[require_support_agent] = lambda: BackofficePrincipal(
        subject="agent-2",
        permissions=frozenset(),
    )
    try:
        response = TestClient(app).get(
            "/support/v1/backoffice/cases/11111111-1111-1111-1111-111111111111/context",
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "BACKOFFICE_PERMISSION_FORBIDDEN"
    finally:
        app.dependency_overrides.pop(require_support_agent, None)
