from __future__ import annotations

import json
from uuid import UUID

import httpx
from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..config import settings
from .auth_context import AuthContext

_PUBLIC_PREFIXES = ("/healthz", "/v1/auth/", "/docs", "/redoc", "/openapi.json")

# Supabase JWKS 캐시 (비대칭 ES256/RS256 서명키 검증용).
# Supabase 신규 프로젝트는 JWT를 ES256(EC P-256) 공개키로 서명하므로,
# 공유 secret(HS256) 대신 JWKS의 공개키로 검증해야 한다.
_jwks_cache: dict | None = None


async def _get_jwks(force: bool = False) -> dict:
    """Supabase JWKS(공개키 집합)를 가져와 캐시한다."""
    global _jwks_cache
    if _jwks_cache is None or force:
        url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(url, headers={"apikey": settings.supabase_anon_key})
        res.raise_for_status()
        _jwks_cache = res.json()
    return _jwks_cache


async def _find_jwk(kid: str | None) -> dict:
    """kid에 해당하는 JWK를 찾는다. 캐시 미스 시 1회 강제 갱신(키 회전 대비)."""
    jwks = await _get_jwks()
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        jwks = await _get_jwks(force=True)
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        raise JWTError(f"JWKS에 매칭되는 kid가 없습니다: {kid}")
    return key


def _payload_to_context(payload: dict) -> AuthContext:
    """검증된 JWT payload를 AuthContext로 변환한다."""
    sub = payload.get("sub")
    if not sub:
        raise ValueError("sub 클레임 없음")
    session_raw = payload.get("session_id", sub)
    try:
        session_id = UUID(str(session_raw))
    except (ValueError, TypeError):
        session_id = UUID(str(sub))
    return AuthContext(
        principal_id=UUID(str(sub)),
        role="principal",
        session_id=session_id,
        email=payload.get("email"),
        scopes=payload.get("scopes", []),
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        token = self._extract_bearer(request)
        if not token:
            return _unauthorized("Bearer 토큰이 없습니다.")

        try:
            ctx = await self._verify(token)
        except (JWTError, ValueError, KeyError, httpx.HTTPError):
            return _unauthorized("유효하지 않은 토큰입니다.")

        request.state.auth = ctx
        return await call_next(request)

    @staticmethod
    def _extract_bearer(request: Request) -> str | None:
        auth = request.headers.get("Authorization", "")
        return auth[7:] if auth.startswith("Bearer ") else None

    @staticmethod
    async def _verify(token: str) -> AuthContext:
        """alg에 따라 dev JWT(HS256) 또는 Supabase JWT(ES256/RS256)를 검증한다."""
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        if alg in ("ES256", "RS256"):
            key = await _find_jwk(header.get("kid"))
            payload = jwt.decode(token, key, algorithms=[alg], options={"verify_aud": False})
            return _payload_to_context(payload)
        # 기본: HS256 (개발용 dev JWT)
        return AuthMiddleware._decode(token)

    @staticmethod
    def _decode(token: str) -> AuthContext:
        """HS256 검증 (개발용 dev JWT, SUPABASE_JWT_SECRET 으로 서명). 단위 테스트에서 직접 사용."""
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return _payload_to_context(payload)


def _unauthorized(message: str) -> Response:
    body = json.dumps({
        "data": None,
        "meta": {},
        "error": {"code": "UNAUTHORIZED", "message": message, "status": 401},
    })
    return Response(content=body, status_code=401, media_type="application/json")
