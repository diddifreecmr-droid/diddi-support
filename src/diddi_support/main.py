from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from diddi_support.core.audit_context import reset_backoffice_reason
from diddi_support.core.auth import ServiceAuthenticationError
from diddi_support.core.config import settings
from diddi_support.core.manifest import load_manifest
from diddi_support.presentation.internal_router import (
    backoffice_router,
)
from diddi_support.presentation.internal_router import (
    router as internal_router,
)

manifest = load_manifest(Path(settings.manifest_path))
app = FastAPI(title=settings.app_name, version=manifest.version)
app.include_router(internal_router)
app.include_router(backoffice_router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.scope["headers"] = [
        (name, value)
        for name, value in request.scope["headers"]
        if name.lower() != b"x-request-id"
    ] + [(b"x-request-id", request_id.encode("latin-1"))]
    try:
        response = await call_next(request)
    finally:
        token = getattr(request.state, "backoffice_reason_token", None)
        if token is not None:
            reset_backoffice_reason(token)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(ServiceAuthenticationError)
def service_authentication_error_handler(_, exc: ServiceAuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": {"code": str(exc)}})


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/ready", tags=["health"])
def readiness() -> JSONResponse:
    status = "ready"
    code = 200
    if settings.require_dependencies and (not settings.database_url or not settings.redis_url):
        status = "not_ready"
        code = 503
    return JSONResponse(
        status_code=code,
        content={
            "status": status,
            "service": settings.app_name,
            "components": {
                "configuration": "ok",
                "database": "configured" if settings.database_url else "not_configured",
                "redis": "configured" if settings.redis_url else "not_configured",
            },
        },
    )


@app.get("/support/v1/ping", tags=["support"])
def ping() -> dict[str, str]:
    return {"module": manifest.module, "protocol": manifest.protocol, "status": "ok"}
