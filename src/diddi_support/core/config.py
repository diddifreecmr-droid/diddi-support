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
    diddifreeid_service_token_url: str = ""
    diddisupport_diddigo_base_url: str = ""
    diddisupport_diddigo_service_client_id: str = ""
    diddisupport_diddigo_service_client_secret: str = ""
    diddisupport_diddigo_service_audience: str = "diddigo"
    diddisupport_diddigo_service_scope: str = "diddigo:support-context:read"
    diddifiles_base_url: str = ""
    diddifiles_auth_token: str = ""
    diddifiles_client_id: str = ""
    attachment_max_bytes: int = Field(default=10_485_760, ge=1, le=104_857_600)
    sos_max_notification_attempts: int = Field(default=3, ge=1, le=10)
    sos_escalation_after_seconds: int = Field(default=60, ge=1, le=86_400)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
