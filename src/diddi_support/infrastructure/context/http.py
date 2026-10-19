from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from diddi_support.application.context import (
    BusinessContext,
    ContextNotFoundError,
    ContextProviderUnavailableError,
)
from diddi_support.core.config import settings


class HttpContextProvider:
    def __init__(
        self,
        *,
        base_url: str,
        scope: str,
        timeout_seconds: float = settings.context_request_timeout_seconds,
        auth_token: str = settings.context_auth_token,
        client_id: str = settings.context_client_id,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.scope = scope
        self.timeout_seconds = timeout_seconds
        self.auth_token = auth_token
        self.client_id = client_id
        self.transport = transport

    async def fetch(
        self,
        *,
        resource_type: str,
        resource_id: UUID,
        request_id: str | None,
    ) -> BusinessContext:
        path = f"/internal/v1/support/{quote(resource_type, safe='')}/{resource_id}/context"
        headers = {
            "Accept": "application/json",
            "X-Support-Context-Scope": self.scope,
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.client_id:
            headers["X-Client-ID"] = self.client_id
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(path, headers=headers)
        except httpx.HTTPError as exc:
            raise ContextProviderUnavailableError("CONTEXT_PROVIDER_UNAVAILABLE") from exc

        if response.status_code == 404:
            raise ContextNotFoundError("CONTEXT_NOT_FOUND")
        if response.status_code in {401, 403}:
            raise ContextProviderUnavailableError("CONTEXT_PROVIDER_FORBIDDEN")
        if response.status_code >= 500:
            raise ContextProviderUnavailableError("CONTEXT_PROVIDER_UNAVAILABLE")
        if response.status_code >= 400:
            raise ContextProviderUnavailableError("CONTEXT_PROVIDER_REJECTED")
        try:
            payload: Any = response.json()
            return BusinessContext.model_validate(payload)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ContextProviderUnavailableError("CONTEXT_PROVIDER_INVALID_RESPONSE") from exc


def providers_from_settings() -> dict[str, HttpContextProvider]:
    if not settings.context_connectors_json:
        return {}
    try:
        config = json.loads(settings.context_connectors_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("CONTEXT_CONNECTORS_JSON_INVALID") from exc
    if not isinstance(config, dict):
        raise RuntimeError("CONTEXT_CONNECTORS_JSON_INVALID")

    providers: dict[str, HttpContextProvider] = {}
    for service, connector in config.items():
        if not isinstance(service, str) or not isinstance(connector, dict):
            raise RuntimeError("CONTEXT_CONNECTORS_JSON_INVALID")
        base_url = connector.get("base_url")
        scope = connector.get("scope")
        if not isinstance(base_url, str) or not isinstance(scope, str):
            raise RuntimeError("CONTEXT_CONNECTORS_JSON_INVALID")
        providers[service] = HttpContextProvider(base_url=base_url, scope=scope)
    return providers
