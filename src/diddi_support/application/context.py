from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BusinessContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: str = Field(pattern=r"^diddi\.context\.v1$")
    origin_service: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    resource_type: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    resource_id: UUID
    data: dict[str, object]
    redacted_fields: list[str] = Field(default_factory=list)
    as_of: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextProvider(Protocol):
    async def fetch(
        self,
        *,
        resource_type: str,
        resource_id: UUID,
        request_id: str | None,
    ) -> BusinessContext: ...


class ContextNotConfiguredError(RuntimeError):
    pass


class ContextNotFoundError(RuntimeError):
    pass


class ContextProviderUnavailableError(RuntimeError):
    pass


class ContextService:
    def __init__(self, providers: Mapping[str, ContextProvider]) -> None:
        self.providers = providers
        self.audit_events: list[dict[str, object]] = []

    async def get_context(
        self,
        *,
        origin_service: str,
        resource_type: str,
        resource_id: UUID,
        request_id: str | None,
    ) -> BusinessContext:
        provider = self.providers.get(origin_service)
        if provider is None:
            raise ContextNotConfiguredError("CONTEXT_PROVIDER_NOT_CONFIGURED")
        context = await provider.fetch(
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
        )
        if context.origin_service != origin_service or context.resource_type != resource_type:
            raise ContextProviderUnavailableError("CONTEXT_RESOURCE_MISMATCH")
        if context.resource_id != resource_id:
            raise ContextProviderUnavailableError("CONTEXT_RESOURCE_MISMATCH")
        self.audit_events.append(
            {
                "action": "support.context.read",
                "origin_service": origin_service,
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "request_id": request_id,
                "fetched_at": context.fetched_at.isoformat(),
            }
        )
        return context
