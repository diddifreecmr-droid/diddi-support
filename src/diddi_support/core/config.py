from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "diddi-support"
    app_env: str = "local"
    log_level: str = "INFO"
    port: int = Field(default=8050, ge=1, le=65535)
    require_dependencies: bool = False
    manifest_path: str = "manifests/diddi-support.v1.json"
    identity_jwks_url: str = ""
    identity_issuer: str = "diddifree-id"
    service_audience: str = "diddi-support"
    backoffice_audience: str = "diddi-comms-backoffice"
    database_url: str = ""
    redis_url: str = ""
    context_connectors_json: str = ""
    context_request_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    context_auth_token: str = ""
    context_client_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
