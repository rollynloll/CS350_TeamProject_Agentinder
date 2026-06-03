"""
test_principal_handler.py — POST /v1/principals 핸들러 및 _decode email 클레임 단위 테스트.

테스트 대상:
  - backend/app/auth/auth_middleware.py::AuthMiddleware._decode (email 클레임 추출)
  - backend/app/handlers/principal_handler.py::create_principal (email/name 우선순위)

호출 위치: pytest 수집 시 자동 실행. DB 연결 없이 mock 처리.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.auth_context import AuthContext
from app.auth.auth_middleware import AuthMiddleware
from app.auth.error_handler_middleware import ErrorHandlerMiddleware
from app.deps import get_auth
from app.handlers.principal_handler import router


# ── 헬퍼 ──────────────────────────────────────────────────────────────────

def make_principal_row(
    principal_id: UUID,
    email: str = "user@example.com",
    name: str = "user",
    plan: str = "free",
) -> dict:
    """asyncpg.Record 대신 dict-like 픽스처."""
    return {
        "principal_id": principal_id,
        "email": email,
        "name": name,
        "plan": plan,
        "mfa_enabled": False,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }


def build_app(auth_ctx: AuthContext) -> FastAPI:
    """테스트용 FastAPI 앱 — get_auth를 auth_ctx로 오버라이드."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_auth] = lambda: auth_ctx
    return app


def build_app_with_error_handler(auth_ctx: AuthContext) -> FastAPI:
    """ErrorHandlerMiddleware 포함 테스트용 앱."""
    app = FastAPI()
    app.include_router(router)
    app.add_middleware(ErrorHandlerMiddleware)
    app.dependency_overrides[get_auth] = lambda: auth_ctx
    return app


# ── _decode email 클레임 추출 테스트 ───────────────────────────────────────

class TestDecodeEmailClaim:
    """AuthMiddleware._decode 가 JWT payload 에서 email 클레임을 추출하는지 검증."""

    def test_decode_extracts_email_when_present(self) -> None:
        """JWT payload 에 email 이 있으면 AuthContext.email 에 담긴다."""
        pid = uuid4()
        payload = {
            "sub": str(pid),
            "session_id": str(pid),
            "email": "test@example.com",
            "scopes": [],
        }
        with patch("app.auth.auth_middleware.jwt") as mock_jwt:
            mock_jwt.decode.return_value = payload
            ctx = AuthMiddleware._decode("fake.token.here")

        assert ctx.email == "test@example.com"
        assert ctx.principal_id == pid

    def test_decode_email_is_none_when_absent(self) -> None:
        """JWT payload 에 email 이 없으면 AuthContext.email 이 None 이다."""
        pid = uuid4()
        payload = {
            "sub": str(pid),
            "session_id": str(pid),
            # email 키 없음
        }
        with patch("app.auth.auth_middleware.jwt") as mock_jwt:
            mock_jwt.decode.return_value = payload
            ctx = AuthMiddleware._decode("fake.token.here")

        assert ctx.email is None

    def test_decode_email_passes_through_exact_value(self) -> None:
        """email 값이 변환 없이 그대로 AuthContext 에 저장된다."""
        pid = uuid4()
        payload = {
            "sub": str(pid),
            "session_id": str(pid),
            "email": "Mixed.Case+tag@Sub.Domain.io",
        }
        with patch("app.auth.auth_middleware.jwt") as mock_jwt:
            mock_jwt.decode.return_value = payload
            ctx = AuthMiddleware._decode("fake.token.here")

        assert ctx.email == "Mixed.Case+tag@Sub.Domain.io"


# ── create_principal email 우선순위 테스트 ─────────────────────────────────

class TestCreatePrincipalEmailPriority:
    """email 우선순위: JWT 클레임 > 요청 바디."""

    async def test_uses_jwt_email_when_available(self) -> None:
        """JWT에 email이 있으면 바디 email을 무시하고 JWT email을 쓴다."""
        pid = uuid4()
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email="jwt@example.com"
        )
        row = make_principal_row(pid, email="jwt@example.com", name="jwt")
        app = build_app(auth_ctx)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=row)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/v1/principals", json={"email": "body@example.com", "name": "Body"}
                )

        assert resp.status_code == 200
        call_args = mock_db.upsert_principal.call_args
        assert call_args.args[1] == "jwt@example.com"

    async def test_uses_body_email_when_jwt_email_absent(self) -> None:
        """JWT에 email이 없으면 바디 email을 사용한다."""
        pid = uuid4()
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email=None
        )
        row = make_principal_row(pid, email="body@example.com", name="body")
        app = build_app(auth_ctx)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=row)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={"email": "body@example.com"})

        assert resp.status_code == 200
        call_args = mock_db.upsert_principal.call_args
        assert call_args.args[1] == "body@example.com"

    async def test_raises_400_when_no_email_available(self) -> None:
        """JWT도 바디도 email이 없으면 ValueError → 400."""
        pid = uuid4()
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email=None
        )
        app = build_app_with_error_handler(auth_ctx)

        with patch("app.handlers.principal_handler.db"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={})

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "BAD_REQUEST"


# ── create_principal name 우선순위 테스트 ──────────────────────────────────

class TestCreatePrincipalNamePriority:
    """name 우선순위: 요청 바디 > email 앞부분 > 'New User'."""

    async def test_uses_body_name_when_provided(self) -> None:
        """바디에 name이 있으면 그것을 name으로 쓴다."""
        pid = uuid4()
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email="user@example.com"
        )
        row = make_principal_row(pid, name="Custom Name")
        app = build_app(auth_ctx)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=row)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={"name": "Custom Name"})

        call_args = mock_db.upsert_principal.call_args
        assert call_args.args[2] == "Custom Name"

    async def test_uses_email_prefix_when_name_absent(self) -> None:
        """바디에 name이 없으면 email @ 앞부분을 name으로 쓴다."""
        pid = uuid4()
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email="jdoe@example.com"
        )
        row = make_principal_row(pid, name="jdoe")
        app = build_app(auth_ctx)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=row)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={})

        call_args = mock_db.upsert_principal.call_args
        assert call_args.args[2] == "jdoe"

    async def test_uses_new_user_fallback_when_email_has_no_at_sign(self) -> None:
        """email에 @ 없으면 name = 'New User'."""
        pid = uuid4()
        # body.email로 email 공급 (@ 없는 값)
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email=None
        )
        row = make_principal_row(pid, email="noemail", name="New User")
        app = build_app(auth_ctx)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=row)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={"email": "noemail"})

        call_args = mock_db.upsert_principal.call_args
        assert call_args.args[2] == "New User"


# ── 인증 권한 테스트 ─────────────────────────────────────────────────────

class TestCreatePrincipalPermissions:
    """인증 관련 예외 처리 테스트."""

    async def test_raises_403_when_principal_id_none(self) -> None:
        """JWT에 principal_id가 없으면 PermissionError → 403."""
        auth_ctx = AuthContext(
            role="principal", session_id=uuid4(), principal_id=None, email="x@y.com"
        )
        app = build_app_with_error_handler(auth_ctx)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/v1/principals", json={"name": "Test"})

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"


# ── 응답 봉투 형태 검증 ───────────────────────────────────────────────────

class TestCreatePrincipalResponseShape:
    """응답 봉투(envelope) 형태 검증."""

    async def test_response_contains_expected_fields(self) -> None:
        """성공 응답에 principal_id, email, name, plan, created_at 이 있어야 한다."""
        pid = uuid4()
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email="resp@example.com"
        )
        row = make_principal_row(pid, email="resp@example.com", name="resp", plan="free")
        app = build_app(auth_ctx)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=row)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={})

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["principal_id"] == str(pid)
        assert data["email"] == "resp@example.com"
        assert data["name"] == "resp"
        assert data["plan"] == "FREE"
        assert "created_at" in data

    async def test_plan_is_uppercase(self) -> None:
        """plan 값이 대문자로 반환된다."""
        pid = uuid4()
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email="p@q.com"
        )
        row = make_principal_row(pid, plan="free")
        app = build_app(auth_ctx)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=row)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={})

        assert resp.json()["data"]["plan"] == "FREE"

    async def test_created_at_is_iso_format_string(self) -> None:
        """created_at이 isoformat 문자열로 반환된다."""
        pid = uuid4()
        auth_ctx = AuthContext(
            role="principal", session_id=pid, principal_id=pid, email="t@t.com"
        )
        row = make_principal_row(pid)
        app = build_app(auth_ctx)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=row)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={})

        created_at = resp.json()["data"]["created_at"]
        assert isinstance(created_at, str)
        # isoformat 파싱 가능 여부 확인
        parsed = datetime.fromisoformat(created_at)
        assert parsed.year == 2024
