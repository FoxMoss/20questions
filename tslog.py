import contextvars
import dataclasses
import time
from typing import Any

import msgspec

_log: "contextvars.ContextVar[RequestLog | None]" = contextvars.ContextVar(
    "ts_log", default=None
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, msgspec.Struct):
        return msgspec.to_builtins(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


class RequestLog:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def record(
        self,
        kind: str,
        request: Any,
        response: Any,
        **meta: Any,
    ) -> None:
        self.entries.append(
            {
                "ts": time.time(),
                "kind": kind,
                "request": _jsonable(request),
                "response": _jsonable(response),
                **meta,
            }
        )

    def as_list(self) -> list[dict]:
        return list(self.entries)


def use(log: RequestLog) -> None:
    """Bind log to the current connection's context."""
    _log.set(log)


def record(kind: str, request: Any, response: Any, **meta: Any) -> None:
    log = _log.get()
    if log is not None:
        log.record(kind, request, response, **meta)
