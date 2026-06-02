from __future__ import annotations

import json
from uuid import UUID

from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..config import settings
from .auth_context import AuthContext

_PUBLIC_PREFIXES = ("/healthz", "/v1/auth/", "/docs", "/redoc", "/openapi.json")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        token = self._extract_bearer(request)
        if not token:
            return _unauthorized("Bearer 토큰이 없습니다.")

        try:
            ctx = self._decode(token)
        except (JWTError, ValueError):
            return _unauthorized("유효하지 않은 토큰입니다.")

        request.state.auth = ctx
        return await call_next(request)

    @staticmethod
    def _extract_bearer(request: Request) -> str | None:
        auth = request.headers.get("Authorization", "")
        return auth[7:] if auth.startswith("Bearer ") else None

    @staticmethod
    def _decode(token: str) -> AuthContext:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        sub = payload.get("sub")
        if not sub:
            raise ValueError("sub 클레임 없음")
        email = payload.get("email")
        return AuthContext(
            principal_id=UUID(sub),
            role="principal",
            session_id=UUID(payload.get("session_id", sub)),
            email=email,
            scopes=payload.get("scopes", []),
        )


def _unauthorized(message: str) -> Response:
    body = json.dumps({
        "data": None,
        "meta": {},
        "error": {"code": "UNAUTHORIZED", "message": message, "status": 401},
    })
    return Response(content=body, status_code=401, media_type="application/json")
