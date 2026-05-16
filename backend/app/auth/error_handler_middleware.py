from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)

_STATUS_MAP: dict[type[Exception], tuple[int, str]] = {
    KeyError: (404, "NOT_FOUND"),
    PermissionError: (403, "FORBIDDEN"),
    ValueError: (400, "BAD_REQUEST"),
    RuntimeError: (500, "INTERNAL_ERROR"),
}


def envelope(
    data: Any = None,
    meta: dict | None = None,
    error: dict | None = None,
) -> dict:
    """표준 응답 봉투 포맷을 반환한다."""
    return {
        "data": data,
        "meta": meta if meta is not None else {},
        "error": error,
    }


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            status, code = 500, "INTERNAL_ERROR"
            for exc_type, (s, c) in _STATUS_MAP.items():
                if isinstance(exc, exc_type):
                    status, code = s, c
                    break

            if status == 500:
                logger.exception("Unhandled exception")

            body = json.dumps({
                "data": None,
                "meta": {},
                "error": {"code": code, "message": str(exc), "status": status},
            })
            return Response(content=body, status_code=status, media_type="application/json")
