from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from diddi_support.core.config import settings
from diddi_support.core.manifest import load_manifest

manifest = load_manifest(Path(settings.manifest_path))
app = FastAPI(title=settings.app_name, version=manifest.version)


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
