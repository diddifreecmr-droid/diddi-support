from __future__ import annotations

from contextvars import ContextVar, Token

_backoffice_reason: ContextVar[str | None] = ContextVar(
    "backoffice_reason",
    default=None,
)


def set_backoffice_reason(reason: str | None) -> Token[str | None]:
    return _backoffice_reason.set(reason)


def reset_backoffice_reason(token: Token[str | None]) -> None:
    # FastAPI/Starlette may execute dependencies in a child context while the
    # HTTP middleware finalizer runs in the parent context.  ContextVar tokens
    # can only be reset in the context that created them; in that case the
    # child context is discarded with the request, so there is nothing to
    # clean up in the parent.
    try:
        _backoffice_reason.reset(token)
    except ValueError:
        return


def get_backoffice_reason() -> str | None:
    return _backoffice_reason.get()
