from __future__ import annotations

import asyncio
import json
import time
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
        token_url: str = "",
        client_secret: str = "",
        audience: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.scope = scope
        self.timeout_seconds = timeout_seconds
        self.auth_token = auth_token
        self.client_id = client_id
        self.token_url = token_url
        self.client_secret = client_secret
        self.audience = audience
        self.transport = transport
        self._token_cache: tuple[str, float] | None = None
        self._token_lock = asyncio.Lock()

    @property
    def service_token_configured(self) -> bool:
        return bool(self.token_url and self.client_id and self.client_secret and self.audience)

    async def _service_access_token(self) -> str:
        now = time.monotonic()
        if self._token_cache and now < self._token_cache[1]:
            return self._token_cache[0]

        async with self._token_lock:
            now = time.monotonic()
            if self._token_cache and now < self._token_cache[1]:
                return self._token_cache[0]
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds,
                    transport=self.transport,
                ) as client:
                    response = await client.post(
                        self.token_url,
                        headers={"X-Client-ID": self.client_id},
                        data={
                            "grant_type": "client_credentials",
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                            "audience": self.audience,
                            "scope": self.scope,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    token = payload["access_token"]
                    expires_in = max(int(payload.get("expires_in", 600)), 1)
                    if not isinstance(token, str) or not token:
                        raise ValueError("missing access_token")
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise ContextProviderUnavailableError(
                    "CONTEXT_AUTHENTICATION_FAILED"
                ) from exc

            self._token_cache = (token, time.monotonic() + max(expires_in - 30, 1))
            return token

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
        if self.service_token_configured:
            headers["Authorization"] = f"Bearer {await self._service_access_token()}"
        elif self.auth_token:
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
    if settings.context_connectors_json:
        try:
            config = json.loads(settings.context_connectors_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("CONTEXT_CONNECTORS_JSON_INVALID") from exc
        if not isinstance(config, dict):
            raise RuntimeError("CONTEXT_CONNECTORS_JSON_INVALID")
    else:
        config = {}

    providers: dict[str, HttpContextProvider] = {}
    for service, connector in config.items():
        if not isinstance(service, str) or not isinstance(connector, dict):
            raise RuntimeError("CONTEXT_CONNECTORS_JSON_INVALID")
        base_url = connector.get("base_url")
        scope = connector.get("scope")
        if not isinstance(base_url, str) or not isinstance(scope, str):
            raise RuntimeError("CONTEXT_CONNECTORS_JSON_INVALID")
        providers[service] = HttpContextProvider(
            base_url=base_url,
            scope=scope,
            token_url=str(connector.get("token_url", "")),
            client_secret=str(connector.get("client_secret", "")),
            audience=str(connector.get("audience", "")),
            client_id=str(connector.get("client_id", settings.context_client_id)),
        )

    if (
        settings.diddisupport_diddigo_base_url
        and settings.diddifreeid_service_token_url
        and settings.diddisupport_diddigo_service_client_id
        and settings.diddisupport_diddigo_service_client_secret
    ):
        providers["diddigo"] = HttpContextProvider(
            base_url=settings.diddisupport_diddigo_base_url,
            scope=settings.diddisupport_diddigo_service_scope,
            token_url=settings.diddifreeid_service_token_url,
            client_id=settings.diddisupport_diddigo_service_client_id,
            client_secret=settings.diddisupport_diddigo_service_client_secret,
            audience=settings.diddisupport_diddigo_service_audience,
        )
    return providers
