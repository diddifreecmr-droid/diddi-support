from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

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
