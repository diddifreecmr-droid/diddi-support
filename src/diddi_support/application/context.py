from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BusinessContext(BaseModel):
    """Versioned envelope returned by a business module to DiddiSupport."""

    model_config = ConfigDict(extra="forbid")

    protocol: str = Field(
        pattern=r"^diddi\.context\.v1$",
        description="Stable context contract identifier.",
    )
    origin_service: str = Field(
        pattern=r"^[a-z][a-z0-9-]{1,63}$",
        description="Service that owns the referenced business resource.",
    )
    resource_type: str = Field(
        pattern=r"^[a-z][a-z0-9_-]{1,63}$",
        description="Owner-defined resource type, for example ride or order.",
    )
    resource_id: UUID = Field(description="Stable identifier of the business resource.")
    data: dict[str, object] = Field(
        description="Minimal support-safe context; the owner remains its source of truth.",
    )
    redacted_fields: list[str] = Field(
        description="Dotted paths intentionally removed or masked from data.",
    )
    as_of: datetime = Field(
        description="Timestamp at which the owner says the business state was current.",
    )
    fetched_at: datetime = Field(
        description="Timestamp at which DiddiSupport received this context."
    )


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
