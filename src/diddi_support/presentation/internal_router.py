from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from diddi_support.core.auth import (
    ServicePrincipal,
    require_support_service,
)
from diddi_support.domain.cases import (
    CasePriority,
    DomainConflictError,
    InMemorySupportCaseRepository,
    SupportCaseService,
)

router = APIRouter(prefix="/support/v1/internal", tags=["internal-support"])
repository = InMemorySupportCaseRepository()
case_service = SupportCaseService(repository)
CREATE_CASE_SCOPE = "diddi-support:cases:create"


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


@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CreateCaseRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: ServicePrincipal = Depends(require_support_service),
) -> CaseResponse:
    if CREATE_CASE_SCOPE not in principal.scopes:
        raise HTTPException(status_code=403, detail={"code": "SERVICE_SCOPE_FORBIDDEN"})
    if principal.subject != f"service:{payload.origin_service}":
        raise HTTPException(status_code=403, detail={"code": "SERVICE_ORIGIN_FORBIDDEN"})
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})

    try:
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
