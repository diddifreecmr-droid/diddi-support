from __future__ import annotations

from datetime import datetime
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, HttpUrl

from diddi_support.core.config import settings
from diddi_support.domain.messages import AttachmentPurpose


class TemporaryFileAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temporary_url: HttpUrl
    expires_at: datetime


class DiddiFilesError(RuntimeError):
    pass


class HttpDiddiFilesClient:
    def __init__(
        self,
        *,
        base_url: str,
        auth_token: str = settings.diddifiles_auth_token,
        client_id: str = settings.diddifiles_client_id,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.client_id = client_id
        self.transport = transport

    async def temporary_access(
        self,
        *,
        file_id: UUID,
        purpose: AttachmentPurpose,
        request_id: str | None,
    ) -> TemporaryFileAccess:
        headers = {"Accept": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.client_id:
            headers["X-Client-ID"] = self.client_id
        if request_id:
            headers["X-Request-ID"] = request_id
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=5,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"/internal/v1/files/{file_id}/temporary-access",
                    headers=headers,
                    json={"purpose": purpose.value},
                )
        except httpx.HTTPError as exc:
            raise DiddiFilesError("DIDDIFILES_UNAVAILABLE") from exc
        if response.status_code == 404:
            raise DiddiFilesError("FILE_NOT_FOUND")
        if response.status_code >= 400:
            raise DiddiFilesError("DIDDIFILES_REJECTED")
        try:
            payload = response.json()
            if payload.get("public_url"):
                raise DiddiFilesError("PUBLIC_FILE_URL_FORBIDDEN")
            return TemporaryFileAccess.model_validate(payload)
        except DiddiFilesError:
            raise
        except (TypeError, ValueError) as exc:
            raise DiddiFilesError("DIDDIFILES_INVALID_RESPONSE") from exc


def client_from_settings() -> HttpDiddiFilesClient | None:
    if not settings.diddifiles_base_url:
        return None
    return HttpDiddiFilesClient(base_url=settings.diddifiles_base_url)
