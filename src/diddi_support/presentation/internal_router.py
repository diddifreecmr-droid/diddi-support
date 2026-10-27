from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from diddi_support.application.actions import ActionService, PersistentActionService
from diddi_support.application.cases import PersistentSupportCaseService
from diddi_support.application.context import (
    BusinessContext,
    ContextNotConfiguredError,
    ContextNotFoundError,
    ContextProviderUnavailableError,
    ContextService,
)
from diddi_support.application.handoff import ConversationModeService
from diddi_support.application.messages import (
    PersistentSupportConversationService,
    SupportConversationService,
)
from diddi_support.application.sos import PersistentSosService, SosService
from diddi_support.core.auth import (
    BackofficePrincipal,
    ServicePrincipal,
    require_support_agent,
    require_support_service,
)
from diddi_support.core.config import settings
from diddi_support.core.database import get_session_optional
from diddi_support.domain.actions import ActionStatus, ActionType, SupportAction
from diddi_support.domain.cases import (
    CasePriority,
    CaseStatus,
    DomainConflictError,
    InMemorySupportCaseRepository,
    InvalidCaseTransition,
    MessageVisibility,
    SupportCaseService,
)
from diddi_support.domain.handoff import ConversationMode, HandoffConflictError
from diddi_support.domain.messages import (
    ALLOWED_ATTACHMENT_MIME_TYPES,
    AttachmentPurpose,
    MessageAuthorType,
    SupportAttachment,
    SupportMessage,
)
from diddi_support.domain.sos import SosAlert, SosHandlingStatus, SosNotificationStatus
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
sos_service = SosService()
action_service = ActionService()
handoff_service = ConversationModeService()
diddifiles_client = client_from_settings()
CREATE_CASE_SCOPE = "diddi-support:cases:create"
READ_CONTEXT_SCOPE = "diddi-support:cases:read"
MESSAGE_WRITE_SCOPE = "diddi-support:messages:write"
BACKOFFICE_READ_PERMISSION = "diddi-support:read"


def _allowed_context_services() -> frozenset[str]:
    return frozenset(
        service.strip()
        for service in settings.context_reader_allowed_services.split(",")
        if service.strip()
    )


def _delegated_origin_allowed(origin_service: str) -> bool:
    return origin_service in {
        service.strip()
        for service in settings.case_delegated_origin_services.split(",")
        if service.strip()
    }


def require_context_reader(
    principal: ServicePrincipal = Depends(require_support_service),
) -> ServicePrincipal:
    """Allow only explicitly registered internal context consumers."""
    if principal.subject.removeprefix("service:") not in _allowed_context_services():
        raise HTTPException(status_code=403, detail={"code": "CONTEXT_CALLER_FORBIDDEN"})
    if (
        principal.subject == "service:diddicomms"
        and settings.diddicomms_service_client_id
        and principal.client_id != settings.diddicomms_service_client_id
    ):
        raise HTTPException(status_code=403, detail={"code": "CONTEXT_CLIENT_ID_FORBIDDEN"})
    return principal


def require_diddicomms(
    principal: ServicePrincipal = Depends(require_support_service),
) -> ServicePrincipal:
    if principal.subject != "service:diddicomms":
        raise HTTPException(status_code=403, detail={"code": "CONTEXT_CALLER_FORBIDDEN"})
    if (
        settings.diddicomms_service_client_id
        and principal.client_id != settings.diddicomms_service_client_id
    ):
        raise HTTPException(status_code=403, detail={"code": "CONTEXT_CLIENT_ID_FORBIDDEN"})
    return principal


class CreateCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin_service: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9-]{1,63}$")
    resource_type: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    resource_id: UUID | None = None
    origin_report_id: str | None = Field(default=None, max_length=160)
    reporter_user_id: UUID
    category: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=200)
    priority: CasePriority = CasePriority.NORMAL

class CaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    case_id: UUID
    origin_service: str | None
    resource_type: str | None
    resource_id: UUID | None
    reporter_user_id: UUID
    category: str
    subject: str
    priority: CasePriority
    status: str
    created: bool
    created_at: datetime


class CaseSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    origin_service: str | None
    resource_type: str | None
    resource_id: UUID | None
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


class CreateUserMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reporter_user_id: UUID
    body: str = Field(min_length=1, max_length=10_000)


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


class CreateSosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reporter_user_id: UUID
    origin_service: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    case_id: UUID | None = None
    source_alert_id: str | None = Field(default=None, max_length=160)
    source_notification_sent: bool = False
    location_latitude: float | None = Field(default=None, ge=-90, le=90)
    location_longitude: float | None = Field(default=None, ge=-180, le=180)


class SosResponse(BaseModel):
    id: UUID
    reporter_user_id: UUID
    origin_service: str
    case_id: UUID | None
    source_alert_id: str | None
    notification_status: SosNotificationStatus
    handling_status: SosHandlingStatus
    notification_attempts: int
    escalation_level: int
    created_at: datetime
    updated_at: datetime


class TimelineEvent(BaseModel):
    type: str
    id: UUID
    occurred_at: datetime
    visibility: MessageVisibility | None = None
    summary: str


class CreateActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    action_type: ActionType
    operation_key: str = Field(min_length=8, max_length=160)


class ActionResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ActionStatus
    provider_reference: str | None = Field(default=None, max_length=160)
    result_code: str | None = Field(default=None, max_length=120)


class ActionResponse(BaseModel):
    id: UUID
    case_id: UUID
    operation_key: str
    action_type: ActionType
    requested_by: str
    status: ActionStatus
    provider_reference: str | None
    result_code: str | None
    created_at: datetime
    updated_at: datetime


class HandoffRequest(BaseModel):
    mode: ConversationMode


class HandoffResponse(BaseModel):
    case_id: UUID
    mode: ConversationMode


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
    reference_fields = (payload.origin_service, payload.resource_type, payload.resource_id)
    if any(value is not None for value in reference_fields) and not all(
        value is not None for value in reference_fields
    ):
        raise HTTPException(
            status_code=422,
            detail={"code": "SUPPORT_RESOURCE_REFERENCE_INCOMPLETE"},
        )
    if principal.subject == "service:diddicomms":
        if (
            settings.diddicomms_service_client_id
            and principal.client_id != settings.diddicomms_service_client_id
        ):
            raise HTTPException(status_code=403, detail={"code": "CONTEXT_CLIENT_ID_FORBIDDEN"})
        if payload.origin_service is not None and not _delegated_origin_allowed(
            payload.origin_service
        ):
            raise HTTPException(status_code=403, detail={"code": "SERVICE_ORIGIN_FORBIDDEN"})
    elif payload.origin_service is None or principal.subject != f"service:{payload.origin_service}":
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
        case_id=case.id,
        origin_service=case.origin_service,
        resource_type=case.resource_type,
        resource_id=case.resource_id,
        reporter_user_id=case.reporter_user_id,
        category=case.category,
        subject=case.subject,
        priority=case.priority,
        status=case.status.value,
        created=created,
        created_at=case.created_at,
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
    principal: ServicePrincipal = Depends(require_context_reader),
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


@router.post(
    "/cases/{case_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user_message(
    case_id: UUID,
    payload: CreateUserMessageRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: ServicePrincipal = Depends(require_diddicomms),
    session: AsyncSession | None = Depends(get_session_optional),
) -> MessageResponse:
    if MESSAGE_WRITE_SCOPE not in principal.scopes:
        raise HTTPException(status_code=403, detail={"code": "SERVICE_SCOPE_FORBIDDEN"})
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})
    case = await _load_case(case_id, session)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    _ensure_case_modifiable(case)
    if payload.reporter_user_id != case.reporter_user_id:
        raise HTTPException(status_code=403, detail={"code": "MESSAGE_AUTHOR_FORBIDDEN"})

    message = SupportMessage(
        case_id=case_id,
        author_type=MessageAuthorType.USER,
        author_id=str(payload.reporter_user_id),
        body=payload.body,
        visibility=MessageVisibility.USER_VISIBLE.value,
    )
    request_payload = {
        "case_id": str(case_id),
        "reporter_user_id": str(payload.reporter_user_id),
        "body": payload.body,
        "visibility": MessageVisibility.USER_VISIBLE.value,
    }
    try:
        if session is None:
            message, _ = conversation_service.create_or_get_message(
                message,
                request_payload=request_payload,
                idempotency_key=idempotency_key,
            )
        else:
            message, _ = await PersistentSupportConversationService(session).create_or_get_message(
                message,
                request_payload=request_payload,
                idempotency_key=idempotency_key,
                actor_id=principal.subject,
                request_id=request.headers.get("X-Request-ID"),
            )
    except DomainConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc
    return _to_message_response(message)


@router.get(
    "/cases/{case_id}/messages",
    response_model=list[MessageResponse],
)
async def list_user_messages(
    case_id: UUID,
    principal: ServicePrincipal = Depends(require_diddicomms),
    session: AsyncSession | None = Depends(get_session_optional),
) -> list[MessageResponse]:
    if READ_CONTEXT_SCOPE not in principal.scopes:
        raise HTTPException(status_code=403, detail={"code": "SERVICE_SCOPE_FORBIDDEN"})
    if await _load_case(case_id, session) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    if session is None:
        messages = conversation_service.list_messages(case_id)
    else:
        messages = await PersistentSupportConversationService(session).list_messages(case_id)
    return [
        _to_message_response(message)
        for message in messages
        if MessageVisibility(message.visibility) == MessageVisibility.USER_VISIBLE
    ]


@router.post("/sos", response_model=SosResponse, status_code=status.HTTP_201_CREATED)
async def create_sos_alert(
    payload: CreateSosRequest,
    request: Request,
    principal: ServicePrincipal = Depends(require_support_service),
    session: AsyncSession | None = Depends(get_session_optional),
) -> SosResponse:
    if "diddi-support:sos:create" not in principal.scopes:
        raise HTTPException(status_code=403, detail={"code": "SERVICE_SCOPE_FORBIDDEN"})
    if principal.subject != f"service:{payload.origin_service}":
        raise HTTPException(status_code=403, detail={"code": "SERVICE_ORIGIN_FORBIDDEN"})
    alert = SosAlert(
        reporter_user_id=payload.reporter_user_id,
        origin_service=payload.origin_service,
        case_id=payload.case_id,
        source_alert_id=payload.source_alert_id,
        source_notification_sent=payload.source_notification_sent,
        location_latitude=payload.location_latitude,
        location_longitude=payload.location_longitude,
    )
    if session is None:
        alert, _ = sos_service.create(alert)
    else:
        alert = await PersistentSosService(session).create(
            alert,
            request_id=request.headers.get("X-Request-ID"),
        )
    return _to_sos_response(alert)


@router.post("/actions/{action_id}/result", response_model=ActionResponse)
async def record_action_result(
    action_id: UUID,
    payload: ActionResultRequest,
    request: Request,
    principal: ServicePrincipal = Depends(require_support_service),
    session: AsyncSession | None = Depends(get_session_optional),
) -> ActionResponse:
    if "diddi-support:actions:write" not in principal.scopes:
        raise HTTPException(status_code=403, detail={"code": "SERVICE_SCOPE_FORBIDDEN"})
    if session is None:
        action = action_service.get(action_id)
    else:
        action = await PersistentActionService(session).get(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail={"code": "ACTION_NOT_FOUND"})
    expected_service = (
        "service:diddipay"
        if action.action_type == ActionType.DIDDIPAY_REFUND
        else "service:diddigo"
    )
    if principal.subject != expected_service:
        raise HTTPException(status_code=403, detail={"code": "ACTION_OWNER_FORBIDDEN"})
    if payload.status == ActionStatus.SUCCEEDED:
        if not payload.provider_reference:
            raise HTTPException(status_code=400, detail={"code": "PROVIDER_REFERENCE_REQUIRED"})
        action.confirm(provider_reference=payload.provider_reference)
    elif payload.status == ActionStatus.FAILED:
        action.fail(result_code=payload.result_code or "PROVIDER_FAILED")
    elif payload.status == ActionStatus.UNKNOWN:
        action.fail(result_code=payload.result_code or "PROVIDER_TIMEOUT", unknown=True)
    else:
        action.mark_pending()
    if session is not None:
        action = await PersistentActionService(session).save(
            action,
            request_id=request.headers.get("X-Request-ID"),
        )
    return _to_action_response(action)


@router.get("/cases/{case_id}/context", response_model=CaseContextResponse)
async def get_case_context(
    case_id: UUID,
    request: Request,
    principal: ServicePrincipal = Depends(require_context_reader),
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


@backoffice_router.post("/cases/{case_id}/transfer", response_model=CaseSnapshot)
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


@backoffice_router.get("/sos", response_model=list[SosResponse])
async def list_backoffice_sos(
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[SosResponse]:
    if "diddi-support:read" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if session is None:
        alerts = sos_service.queue(limit=limit)
    else:
        alerts = await PersistentSosService(session).queue(limit=limit)
    return [_to_sos_response(alert) for alert in alerts]


@backoffice_router.post(
    "/actions",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_backoffice_action(
    payload: CreateActionRequest,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> ActionResponse:
    if "diddi-support:write" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if await _load_case(payload.case_id, session) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    if session is None:
        action, _ = action_service.request(
            SupportAction(
                case_id=payload.case_id,
                operation_key=payload.operation_key,
                action_type=payload.action_type,
                requested_by=principal.subject,
            )
        )
    else:
        persistent = PersistentActionService(session)
        action = await persistent.get_by_operation_key(payload.operation_key)
        if action is None:
            action = SupportAction(
                case_id=payload.case_id,
                operation_key=payload.operation_key,
                action_type=payload.action_type,
                requested_by=principal.subject,
            )
            action.mark_pending()
            action = await persistent.add(
                action,
                request_id=request.headers.get("X-Request-ID"),
            )
    return _to_action_response(action)


@backoffice_router.get("/actions/{action_id}", response_model=ActionResponse)
async def get_backoffice_action(
    action_id: UUID,
    session: AsyncSession | None = Depends(get_session_optional),
    principal: BackofficePrincipal = Depends(require_support_agent),
) -> ActionResponse:
    if "diddi-support:read" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if session is None:
        action = action_service.get(action_id)
    else:
        action = await PersistentActionService(session).get(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail={"code": "ACTION_NOT_FOUND"})
    return _to_action_response(action)


@backoffice_router.post("/sos/{alert_id}/confirm", response_model=SosResponse)
async def confirm_backoffice_sos(
    alert_id: UUID,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> SosResponse:
    if "diddi-support:sos-operate" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    alert = await _load_sos(alert_id, session)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "SOS_NOT_FOUND"})
    alert.confirm()
    alert = await _save_sos(alert, session, "support.sos.acknowledged", principal.subject, request)
    return _to_sos_response(alert)


@backoffice_router.post("/sos/{alert_id}/start", response_model=SosResponse)
async def start_backoffice_sos(
    alert_id: UUID,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> SosResponse:
    if "diddi-support:sos-operate" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    alert = await _load_sos(alert_id, session)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "SOS_NOT_FOUND"})
    try:
        alert.start()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "SOS_CONFIRMATION_REQUIRED"}) from exc
    alert = await _save_sos(alert, session, "support.sos.started", principal.subject, request)
    return _to_sos_response(alert)


@backoffice_router.post("/sos/{alert_id}/complete", response_model=SosResponse)
async def complete_backoffice_sos(
    alert_id: UUID,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> SosResponse:
    if "diddi-support:sos-operate" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    alert = await _load_sos(alert_id, session)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "SOS_NOT_FOUND"})
    try:
        alert.complete()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "SOS_CONFIRMATION_REQUIRED"}) from exc
    alert = await _save_sos(alert, session, "support.sos.completed", principal.subject, request)
    return _to_sos_response(alert)


@backoffice_router.post("/sos/{alert_id}/retry-notification", response_model=SosResponse)
async def retry_backoffice_sos_notification(
    alert_id: UUID,
    request: Request,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> SosResponse:
    if "diddi-support:sos-operate" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    alert = await _load_sos(alert_id, session)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "SOS_NOT_FOUND"})
    alert.retry_notification(max_attempts=settings.sos_max_notification_attempts)
    alert = await _save_sos(
        alert,
        session,
        "support.sos.notification.retry",
        principal.subject,
        request,
    )
    return _to_sos_response(alert)


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
    case = await _load_case(case_id, session)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    _ensure_case_modifiable(case)
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


@backoffice_router.get("/cases/{case_id}/timeline", response_model=list[TimelineEvent])
async def list_backoffice_timeline(
    case_id: UUID,
    principal: BackofficePrincipal = Depends(require_support_agent),
    session: AsyncSession | None = Depends(get_session_optional),
) -> list[TimelineEvent]:
    if "diddi-support:read" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    case = await _load_case(case_id, session)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    if session is None:
        messages = list(conversation_service.list_messages(case_id))
        attachments = list(conversation_service.list_attachments(case_id))
    else:
        conversation = PersistentSupportConversationService(session)
        messages = await conversation.list_messages(case_id)
        attachments = await conversation.list_attachments(case_id)
    events = [
        TimelineEvent(
            type="case.created",
            id=case.id,
            occurred_at=case.created_at,
            summary="Support case created",
        )
    ]
    events.extend(
        TimelineEvent(
            type="message.created",
            id=message.id,
            occurred_at=message.created_at,
            visibility=MessageVisibility(message.visibility),
            summary="Support message",
        )
        for message in messages
    )
    events.extend(
        TimelineEvent(
            type="attachment.referenced",
            id=attachment.id,
            occurred_at=attachment.created_at,
            summary="Evidence attachment referenced",
        )
        for attachment in attachments
    )
    return sorted(events, key=lambda event: event.occurred_at)


@backoffice_router.post("/cases/{case_id}/handoff", response_model=HandoffResponse)
async def update_backoffice_handoff(
    case_id: UUID,
    payload: HandoffRequest,
    principal: BackofficePrincipal = Depends(require_support_agent),
) -> HandoffResponse:
    if "diddi-support:reply" not in principal.permissions:
        raise HTTPException(status_code=403, detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"})
    if case_service.repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
    try:
        if payload.mode == ConversationMode.HUMAN_REQUESTED:
            mode = handoff_service.request_human(case_id)
        elif payload.mode == ConversationMode.HUMAN_ACTIVE:
            if "diddi-support:write" not in principal.permissions:
                raise HTTPException(
                    status_code=403,
                    detail={"code": "BACKOFFICE_PERMISSION_FORBIDDEN"},
                )
            mode = handoff_service.activate_human(case_id)
        else:
            raise HTTPException(status_code=400, detail={"code": "AI_MODE_CANNOT_BE_FORCED"})
    except HandoffConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc
    return HandoffResponse(case_id=case_id, mode=mode)


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


async def _load_sos(alert_id: UUID, session: AsyncSession | None):
    if session is None:
        return sos_service.get(alert_id)
    return await PersistentSosService(session).get(alert_id)


async def _save_sos(alert, session, action: str, actor_id: str, request: Request):
    if session is None:
        return alert
    return await PersistentSosService(session).save(
        alert,
        action=action,
        actor_id=actor_id,
        request_id=request.headers.get("X-Request-ID"),
    )


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


def _ensure_case_modifiable(case) -> None:
    if case.status in {CaseStatus.RESOLVED, CaseStatus.CLOSED}:
        raise HTTPException(status_code=409, detail={"code": "CASE_NOT_MODIFIABLE"})


def _to_sos_response(alert: SosAlert) -> SosResponse:
    return SosResponse(
        id=alert.id,
        reporter_user_id=alert.reporter_user_id,
        origin_service=alert.origin_service,
        case_id=alert.case_id,
        source_alert_id=alert.source_alert_id,
        notification_status=alert.notification_status,
        handling_status=alert.handling_status,
        notification_attempts=alert.notification_attempts,
        escalation_level=alert.escalation_level,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


def _to_action_response(action: SupportAction) -> ActionResponse:
    return ActionResponse(
        id=action.id,
        case_id=action.case_id,
        operation_key=action.operation_key,
        action_type=action.action_type,
        requested_by=action.requested_by,
        status=action.status,
        provider_reference=action.provider_reference,
        result_code=action.result_code,
        created_at=action.created_at,
        updated_at=action.updated_at,
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
