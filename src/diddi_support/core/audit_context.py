from __future__ import annotations

from contextvars import ContextVar, Token

_backoffice_reason: ContextVar[str | None] = ContextVar(
    "backoffice_reason",
    default=None,
)


def set_backoffice_reason(reason: str | None) -> Token[str | None]:
    return _backoffice_reason.set(reason)


def reset_backoffice_reason(token: Token[str | None]) -> None:
    _backoffice_reason.reset(token)


def get_backoffice_reason() -> str | None:
    return _backoffice_reason.get()
