from __future__ import annotations

from contextvars import ContextVar


_request_context: ContextVar[dict] = ContextVar("request_context", default={})


def set_request_context(values: dict) -> None:
    _request_context.set(values)


def get_request_context() -> dict:
    return dict(_request_context.get() or {})


def clear_request_context() -> None:
    _request_context.set({})
