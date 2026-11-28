from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Header, Request
from jwt import InvalidTokenError, PyJWKClient

from diddi_support.core.audit_context import set_backoffice_reason
from diddi_support.core.config import settings


@dataclass(frozen=True)
class ServicePrincipal:
    subject: str
    client_id: str
    scopes: frozenset[str]


@dataclass(frozen=True)
class BackofficePrincipal:
    subject: str
    permissions: frozenset[str]
    service_subject: str | None = None
    client_id: str | None = None
    reason: str | None = None


class ServiceAuthenticationError(ValueError):
    """Raised when a service token cannot be trusted."""


def validate_service_claims(claims: dict) -> str:
    """Validate the stable DiddiFreeID service identity claims."""
    if (
        claims.get("token_type") != "service"
        or claims.get("role") != "service"
        or claims.get("status") != "active"
    ):
        raise ServiceAuthenticationError("SERVICE_TOKEN_INVALID")
    subject = claims.get("sub")
    service = claims.get("service")
    if (
        not isinstance(subject, str)
        or not subject.startswith("service:")
        or not isinstance(service, str)
        or service != subject.removeprefix("service:")
    ):
        raise ServiceAuthenticationError("SERVICE_IDENTITY_INVALID")
    return subject


class ServiceTokenVerifier:
    def __init__(self, *, jwks_url: str, issuer: str, audience: str) -> None:
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience

    def verify(self, token: str, client_id: str) -> ServicePrincipal:
        if not self.jwks_url:
            raise ServiceAuthenticationError("IDENTITY_JWKS_URL is not configured")
        try:
            signing_key = PyJWKClient(self.jwks_url).get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["iss", "aud", "sub", "exp"]},
            )
        except (InvalidTokenError, OSError, ValueError) as exc:
            raise ServiceAuthenticationError("SERVICE_TOKEN_INVALID") from exc

        subject = validate_service_claims(claims)
        if claims.get("client_id") != client_id:
            raise ServiceAuthenticationError("SERVICE_CLIENT_ID_INVALID")
        scopes = frozenset(str(claims.get("scope", "")).split())
        return ServicePrincipal(subject=subject, client_id=client_id, scopes=scopes)


def require_support_service(
    authorization: str | None = Header(default=None, alias="Authorization"),
    client_id: str | None = Header(default=None, alias="X-Client-ID"),
) -> ServicePrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise ServiceAuthenticationError("SERVICE_TOKEN_REQUIRED")
    if not client_id:
        raise ServiceAuthenticationError("SERVICE_CLIENT_ID_INVALID")
    token = authorization.removeprefix("Bearer ").strip()
    return ServiceTokenVerifier(
        jwks_url=settings.identity_jwks_url,
        issuer=settings.identity_issuer,
        audience=settings.service_audience,
    ).verify(token, client_id)


class BackofficeTokenVerifier:
    def __init__(self, *, jwks_url: str, issuer: str, audience: str) -> None:
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience

    def verify(self, token: str) -> BackofficePrincipal:
        if not self.jwks_url:
            raise ServiceAuthenticationError("IDENTITY_JWKS_URL is not configured")
        try:
            signing_key = PyJWKClient(self.jwks_url).get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["iss", "aud", "sub", "exp"]},
            )
        except (InvalidTokenError, OSError, ValueError) as exc:
            raise ServiceAuthenticationError("BACKOFFICE_TOKEN_INVALID") from exc

        if claims.get("token_type") != "user" or claims.get("status") != "active":
            raise ServiceAuthenticationError("BACKOFFICE_TOKEN_INVALID")
        raw_permissions = claims.get("permissions", [])
        if isinstance(raw_permissions, str):
            permissions = frozenset(raw_permissions.split())
        elif isinstance(raw_permissions, list):
            permissions = frozenset(str(permission) for permission in raw_permissions)
        else:
            raise ServiceAuthenticationError("BACKOFFICE_TOKEN_INVALID")
        return BackofficePrincipal(subject=str(claims["sub"]), permissions=permissions)


def require_support_agent(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    client_id: str | None = Header(default=None, alias="X-Client-ID"),
    actor: str | None = Header(default=None, alias="X-Backoffice-Actor"),
    reason: str | None = Header(default=None, alias="X-Backoffice-Reason"),
) -> BackofficePrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise ServiceAuthenticationError("BACKOFFICE_TOKEN_REQUIRED")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        unverified_claims = jwt.decode(token, options={"verify_signature": False})
    except InvalidTokenError as exc:
        raise ServiceAuthenticationError("BACKOFFICE_TOKEN_INVALID") from exc

    if unverified_claims.get("token_type") == "service":
        if not client_id:
            raise ServiceAuthenticationError("SERVICE_CLIENT_ID_INVALID")
        allowed_client_ids = frozenset(
            item.strip()
            for item in settings.backoffice_service_client_ids.split(",")
            if item.strip()
        )
        if client_id not in allowed_client_ids:
            raise ServiceAuthenticationError("BACKOFFICE_CLIENT_ID_FORBIDDEN")
        service_principal = ServiceTokenVerifier(
            jwks_url=settings.identity_jwks_url,
            issuer=settings.identity_issuer,
            audience=settings.service_audience,
        ).verify(token, client_id)
        if service_principal.subject != "service:diddiadmin":
            raise ServiceAuthenticationError("BACKOFFICE_SERVICE_FORBIDDEN")
        if not actor:
            raise ServiceAuthenticationError("BACKOFFICE_ACTOR_REQUIRED")
        try:
            UUID(actor)
        except ValueError as exc:
            raise ServiceAuthenticationError("BACKOFFICE_ACTOR_INVALID") from exc
        if reason is not None and len(reason) > 200:
            raise ServiceAuthenticationError("BACKOFFICE_REASON_INVALID")
        request.state.backoffice_reason_token = set_backoffice_reason(reason)
        return BackofficePrincipal(
            subject=actor,
            permissions=service_principal.scopes,
            service_subject=service_principal.subject,
            client_id=client_id,
            reason=reason,
        )

    return BackofficeTokenVerifier(
        jwks_url=settings.identity_jwks_url,
        issuer=settings.identity_issuer,
        audience=settings.backoffice_audience,
    ).verify(token)
