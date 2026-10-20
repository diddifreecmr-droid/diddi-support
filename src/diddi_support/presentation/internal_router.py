from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from diddi_support.application.cases import PersistentSupportCaseService
from diddi_support.application.context import (
    BusinessContext,
    ContextNotConfiguredError,
    ContextNotFoundError,
    ContextProviderUnavailableError,
    ContextService,
)
from diddi_support.application.messages import (
    PersistentSupportConversationService,
    SupportConversationService,
)
from diddi_support.core.auth import (
    BackofficePrincipal,
    ServicePrincipal,
    require_support_agent,
    require_support_service,
)
from diddi_support.core.config import settings
from diddi_support.core.database import get_session_optional
from diddi_support.domain.cases import (
    CasePriority,
    CaseStatus,
    DomainConflictError,
    InMemorySupportCaseRepository,
    InvalidCaseTransition,
    MessageVisibility,
    SupportCaseService,
)
from diddi_support.domain.messages import (
    ALLOWED_ATTACHMENT_MIME_TYPES,
    AttachmentPurpose,
    MessageAuthorType,
    SupportAttachment,
    SupportMessage,
)
from diddi_support.infrastructure.context.http import providers_from_settings
from diddi_support.infrastructure.files.client import (
    DiddiFilesError,
    TemporaryFileAccess,
    client_from_settings,
)
from diddi_support.infrastructure.persistence.repository import PostgresSupportCaseRepository

router = APIRouter(prefix="/support/v1/internal", tags=["internal-support"])
backoffice_router = APIRouter(prefix="/support/v1/backoffice", tags=["backoffice-support"])
repository = InMemorySupportCaseRepository()
case_service = SupportCaseService(repository)
context_service = ContextService(providers_from_settings())
conversation_service = SupportConversationService()
diddifiles_client = client_from_settings()
CREATE_CASE_SCOPE = "diddi-support:cases:create"
READ_CONTEXT_SCOPE = "diddi-support:cases:read"
BACKOFFICE_READ_PERMISSION = "diddi-support:read"


class CreateCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin_service: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    resource_type: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    resource_id: UUID
    origin_report_id: str | None = Field(default=None, max_length=160)
    reporter_user_id: UUID
    category: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=200)
    priority: CasePriority = CasePriority.NORMAL


class CaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    origin_service: str
    resource_type: str
    resource_id: UUID
    reporter_user_id: UUID
    category: str
    subject: str
    priority: CasePriority
    status: str
    created: bool


class CaseSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    origin_service: str
    resource_type: str
    resource_id: UUID
    reporter_user_id: UUID
    category: str
    subject: str
    priority: CasePriority
    status: str
    assigned_agent_id: UUID | None = None


class CaseContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case: CaseSnapshot
    context: BusinessContext


class AssignCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: UUID


class TransitionCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CaseStatus


class CreateMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=10_000)
    visibility: MessageVisibility


class MessageResponse(BaseModel):
    id: UUID
    case_id: UUID
    author_type: MessageAuthorType
    author_id: str
    body: str
    visibility: MessageVisibility
    created_at: datetime


class CreateAttachmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: UUID
    owner_user_id: UUID
    purpose: AttachmentPurpose
    mime_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(gt=0)


class AttachmentResponse(BaseModel):
    id: UUID
    case_id: UUID
    file_id: UUID
    owner_user_id: UUID
    purpose: AttachmentPurpose
    mime_type: str
    size_bytes: int
    created_at: datetime


@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CreateCaseRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: ServicePrincipal = Depends(require_support_service),
    session: AsyncSession | None = Depends(get_session_optional),
) -> CaseResponse:
    if CREATE_CASE_SCOPE not in principal.scopes:
        raise HTTPException(status_code=403, detail={"code": "SERVICE_SCOPE_FORBIDDEN"})
    if principal.subject != f"service:{payload.origin_service}":
        raise HTTPException(status_code=403, detail={"code": "SERVICE_ORIGIN_FORBIDDEN"})
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})

    try:
        if session is None:
            case, created = case_service.open_case(
                origin_service=payload.origin_service,
                resource_type=payload.resource_type,
                resource_id=payload.resource_id,
                reporter_user_id=payload.reporter_user_id,
                category=payload.category,
                subject=payload.subject,
                origin_report_id=payload.origin_report_id,
                priority=payload.priority,
                idempotency_key=idempotency_key,
                request_id=request.headers.get("X-Request-ID"),
            )
        else:
            case, created = await PersistentSupportCaseService(session).open_case(
                origin_service=payload.origin_service,
                resource_type=payload.resource_type,
                resource_id=payload.resource_id,
                reporter_user_id=payload.reporter_user_id,
                category=payload.category,
                subject=payload.subject,
                origin_report_id=payload.origin_report_id,
                priority=payload.priority,
                idempotency_key=idempotency_key,
                request_id=request.headers.get("X-Request-ID"),
            )
    except DomainConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc

    return CaseResponse(
        id=case.id,
        origin_service=case.origin_service,
        resource_type=case.resource_type,
        resource_id=case.resource_id,
        reporter_user_id=case.reporter_user_id,
        category=case.category,
        subject=case.subject,
        priority=case.priority,
        status=case.status.value,
        created=created,
    )


@router.get(
    "/context/{origin_service}/{resource_type}/{resource_id}",
    response_model=BusinessContext,
)
async def get_business_context(
    origin_service: str,
    resource_type: str,
    resource_id: UUID,
    request: Request,
    principal: ServicePrincipal = Depends(require_support_service),
    session: AsyncSession | None = Depends(get_session_optional),
) -> BusinessContext:
    if READ_CONTEXT_SCOPE not in principal.scopes:
        raise HTTPException(status_code=403, detail={"code": "SERVICE_SCOPE_FORBIDDEN"})

    try:
        context = await context_service.get_context(
            origin_service=origin_service,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request.headers.get("X-Request-ID"),
        )
        await _record_context_access(
            session=session,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=principal.subject,
            request_id=request.headers.get("X-Request-ID"),
            fetched_at=context.fetched_at,
        )
        return context
    except (ContextNotConfiguredError, ContextNotFoundError) as exc:
        raise HTTPException(status_code=404, detail={"code": str(exc)}) from exc
    except ContextProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc


@router.get("/cases/{case_id}/context", response_model=CaseContextResponse)
async def get_case_context(
    case_id: UUID,
    request: Request,
    principal: ServicePrincipal = Depends(require_support_service),
    session: AsyncSession | None = Depends(get_session_optional),
) -> CaseContextResponse:
    if READ_CONTEXT_SCOPE not in principal.scopes:
        raise HTTPException(status_code=403, detail={"code": "SERVICE_SCOPE_FORBIDDEN"})

    return await _read_case_context(
        case_id=case_id,
        request=request,
        session=session,
        actor_id=principal.subject,
    )


@backoffice_router.get("/cases", response_model=list[CaseSnapshot])
async def list_backoffice_cases(
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
    case_status: CaseStatus | None = Query(default=None, alias="status"),
    priority: CasePriority | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[CaseSnapshot]:
    if BACKOFFICE_READ_PERMISSION not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if session is None:
        cases = case_service.repository.list(status=case_status, priority=priority, limit=limit)
    else:
        cases = await PersistentSupportCaseService(session).list(
            status=case_status,
            priority=priority,
            limit=limit,
        )
    return [_to_snapshot(case) for case in cases]


@backoffice_router.post("/cases/{case_id}/assign", response_model=CaseSnapshot)
async def assign_backoffice_case(
    case_id: UUID,
    payload: AssignCaseRequest,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> CaseSnapshot:
    if "diddi-support:assign" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if session is None:
        case = case_service.assign_case(
            case_id,
            payload.agent_id,
            actor_id=principal.subject,
            request_id=request.headers.get("X-Request-ID"),
        )
    else:
        case = await PersistentSupportCaseService(session).assign_case(
            case_id,
            payload.agent_id,
            actor_id=principal.subject,
            request_id=request.headers.get("X-Request-ID"),
        )
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    return _to_snapshot(case)


@backoffice_router.post("/cases/{case_id}/transition", response_model=CaseSnapshot)
async def transition_backoffice_case(
    case_id: UUID,
    payload: TransitionCaseRequest,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> CaseSnapshot:
    if "diddi-support:write" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    try:
        if session is None:
            case = case_service.transition_case(
                case_id,
                payload.status,
                actor_id=principal.subject,
                request_id=request.headers.get("X-Request-ID"),
            )
        else:
            case = await PersistentSupportCaseService(session).transition_case(
                case_id,
                payload.status,
                actor_id=principal.subject,
                request_id=request.headers.get("X-Request-ID"),
            )
    except InvalidCaseTransition as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "INVALID_CASE_TRANSITION", "message": str(exc)},
        ) from exc
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    return _to_snapshot(case)


@backoffice_router.post("/cases/{case_id}/messages", response_model=MessageResponse)
async def add_backoffice_message(
    case_id: UUID,
    payload: CreateMessageRequest,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> MessageResponse:
    if payload.visibility == MessageVisibility.USER_VISIBLE:
        required_permission = "diddi-support:reply"
    elif payload.visibility == MessageVisibility.INTERNAL_NOTE:
        required_permission = "diddi-support:write"
    else:
        raise HTTPException(status_code=400, detail={"code": "SYSTEM_MESSAGE_FORBIDDEN"})
    if required_permission not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if await _load_case(case_id, session) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    message = SupportMessage(
        case_id=case_id,
        author_type=MessageAuthorType.AGENT,
        author_id=principal.subject,
        body=payload.body,
        visibility=payload.visibility.value,
    )
    if session is None:
        message = conversation_service.add_message(message)
    else:
        message = await PersistentSupportConversationService(session).add_message(
            message,
            actor_id=principal.subject,
            request_id=request.headers.get("X-Request-ID"),
        )
    return _to_message_response(message)


@backoffice_router.get("/cases/{case_id}/messages", response_model=list[MessageResponse])
async def list_backoffice_messages(
    case_id: UUID,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> list[MessageResponse]:
    if "diddi-support:read" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if await _load_case(case_id, session) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    if session is None:
        messages = conversation_service.list_messages(case_id)
    else:
        messages = await PersistentSupportConversationService(session).list_messages(case_id)
    return [_to_message_response(message) for message in messages]


@backoffice_router.post("/cases/{case_id}/attachments", response_model=AttachmentResponse)
async def add_backoffice_attachment(
    case_id: UUID,
    payload: CreateAttachmentRequest,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> AttachmentResponse:
    if "diddi-support:reply" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    case = await _load_case(case_id, session)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    if payload.owner_user_id != case.reporter_user_id:
        raise HTTPException(status_code=403, detail={"code": "ATTACHMENT_OWNER_MISMATCH"})
    if payload.size_bytes > settings.attachment_max_bytes:
        raise HTTPException(status_code=413, detail={"code": "ATTACHMENT_TOO_LARGE"})
    if payload.mime_type not in ALLOWED_ATTACHMENT_MIME_TYPES[payload.purpose]:
        raise HTTPException(status_code=415, detail={"code": "ATTACHMENT_MIME_FORBIDDEN"})
    attachment = SupportAttachment(
        case_id=case_id,
        file_id=payload.file_id,
        owner_user_id=payload.owner_user_id,
        purpose=payload.purpose,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
    )
    if session is None:
        attachment = conversation_service.add_attachment(attachment)
    else:
        attachment = await PersistentSupportConversationService(session).add_attachment(
            attachment,
            actor_id=principal.subject,
            request_id=request.headers.get("X-Request-ID"),
        )
    return _to_attachment_response(attachment)


@backoffice_router.get(
    "/cases/{case_id}/attachments",
    response_model=list[AttachmentResponse],
)
async def list_backoffice_attachments(
    case_id: UUID,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> list[AttachmentResponse]:
    if "diddi-support:attachments-read" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if await _load_case(case_id, session) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    if session is None:
        attachments = conversation_service.list_attachments(case_id)
    else:
        attachments = await PersistentSupportConversationService(session).list_attachments(case_id)
    return [_to_attachment_response(attachment) for attachment in attachments]


@backoffice_router.post(
    "/cases/{case_id}/attachments/{attachment_id}/temporary-access",
    response_model=TemporaryFileAccess,
)
async def get_attachment_temporary_access(
    case_id: UUID,
    attachment_id: UUID,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> TemporaryFileAccess:
    if "diddi-support:attachments-read" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if session is None:
        attachment = conversation_service.get_attachment(attachment_id)
    else:
        attachment = await PersistentSupportConversationService(session).get_attachment(
            attachment_id
        )
    if attachment is None or attachment.case_id != case_id:
        raise HTTPException(status_code=404, detail={"code": "ATTACHMENT_NOT_FOUND"})
    if diddifiles_client is None:
        raise HTTPException(status_code=503, detail={"code": "DIDDIFILES_NOT_CONFIGURED"})
    try:
        return await diddifiles_client.temporary_access(
            file_id=attachment.file_id,
            purpose=attachment.purpose,
            request_id=request.headers.get("X-Request-ID"),
        )
    except DiddiFilesError as exc:
        status_code = 404 if str(exc) == "FILE_NOT_FOUND" else 503
        raise HTTPException(status_code=status_code, detail={"code": str(exc)}) from exc


@backoffice_router.get("/cases/{case_id}/context", response_model=CaseContextResponse)
async def get_backoffice_case_context(
    case_id: UUID,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> CaseContextResponse:
    if BACKOFFICE_READ_PERMISSION not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    return await _read_case_context(
        case_id=case_id,
        request=request,
        session=session,
        actor_id=principal.subject,
    )


async def _load_case(case_id: UUID, session: AsyncSession | None):
    if session is None:
        return case_service.repository.get(case_id)
    return await PersistentSupportCaseService(session).get(case_id)


def _to_snapshot(case) -> CaseSnapshot:
    return CaseSnapshot(
        id=case.id,
        origin_service=case.origin_service,
        resource_type=case.resource_type,
        resource_id=case.resource_id,
        reporter_user_id=case.reporter_user_id,
        category=case.category,
        subject=case.subject,
        priority=case.priority,
        status=case.status.value,
        assigned_agent_id=case.assigned_agent_id,
    )


def _to_message_response(message: SupportMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        case_id=message.case_id,
        author_type=message.author_type,
        author_id=message.author_id,
        body=message.body,
        visibility=MessageVisibility(message.visibility),
        created_at=message.created_at,
    )


def _to_attachment_response(attachment: SupportAttachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=attachment.id,
        case_id=attachment.case_id,
        file_id=attachment.file_id,
        owner_user_id=attachment.owner_user_id,
        purpose=attachment.purpose,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        created_at=attachment.created_at,
    )


async def _read_case_context(
    *,
    case_id: UUID,
    request: Request,
    session: AsyncSession | None,
    actor_id: str,
) -> CaseContextResponse:
    if session is None:
        case = case_service.repository.get(case_id)
    else:
        case = await PersistentSupportCaseService(session).get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})

    try:
        context = await context_service.get_context(
            origin_service=case.origin_service,
            resource_type=case.resource_type,
            resource_id=case.resource_id,
            request_id=request.headers.get("X-Request-ID"),
        )
    except (ContextNotConfiguredError, ContextNotFoundError) as exc:
        raise HTTPException(status_code=404, detail={"code": str(exc)}) from exc
    except ContextProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail={"code": str(exc)}) from exc

    await _record_context_access(
        session=session,
        resource_type=case.resource_type,
        resource_id=case.resource_id,
        actor_id=actor_id,
        request_id=request.headers.get("X-Request-ID"),
        fetched_at=context.fetched_at,
    )

    return CaseContextResponse(
        case=_to_snapshot(case),
        context=context,
    )


async def _record_context_access(
    *,
    session: AsyncSession | None,
    resource_type: str,
    resource_id: UUID,
    actor_id: str,
    request_id: str | None,
    fetched_at,
) -> None:
    if session is None:
        return
    await PostgresSupportCaseRepository(session).record_context_access(
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        request_id=request_id,
        fetched_at=fetched_at,
    )
