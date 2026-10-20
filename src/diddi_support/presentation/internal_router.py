from __future__ import annotations

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
from diddi_support.core.auth import (
    BackofficePrincipal,
    ServicePrincipal,
    require_support_agent,
    require_support_service,
)
from diddi_support.core.database import get_session_optional
from diddi_support.domain.cases import (
    CasePriority,
    CaseStatus,
    DomainConflictError,
    InMemorySupportCaseRepository,
    InvalidCaseTransition,
    SupportCaseService,
)
from diddi_support.infrastructure.context.http import providers_from_settings
from diddi_support.infrastructure.persistence.repository import PostgresSupportCaseRepository

router = APIRouter(prefix="/support/v1/internal", tags=["internal-support"])
backoffice_router = APIRouter(prefix="/support/v1/backoffice", tags=["backoffice-support"])
repository = InMemorySupportCaseRepository()
case_service = SupportCaseService(repository)
context_service = ContextService(providers_from_settings())
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
