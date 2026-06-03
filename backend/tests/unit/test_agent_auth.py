"""
test_agent_auth.py — X-Agent-Key(에이전트 API key) 인증 단위/통합 테스트.

테스트 대상:
  - backend/app/auth/auth_middleware.py::AuthMiddleware._verify_agent_key
  - backend/app/auth/auth_middleware.py::AuthMiddleware.dispatch (X-Agent-Key 분기)

호출 위치: pytest 수집 시 자동 실행. db 는 mock 처리.
"""
from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.auth.auth_middleware import AuthMiddleware


class TestVerifyAgentKey:
    """_verify_agent_key 가 API key 를 검증하고 에이전트 AuthContext 를 만든다."""

    async def test_valid_key_creates_agent_context(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        with patch("app.auth.auth_middleware.db") as mock_db:
            mock_db.get_agent_by_api_key_hash = AsyncMock(
                return_value={"agent_id": agent_id, "principal_id": principal_id}
            )
            ctx = await AuthMiddleware._verify_agent_key("some-api-key")

        assert ctx.role == "agent"
        assert ctx.is_agent() is True
        assert ctx.agent_id == agent_id
        assert ctx.principal_id == principal_id

    async def test_key_is_hashed_with_sha256(self) -> None:
        """조회 시 평문이 아니라 sha256 hex 해시로 DB를 조회한다."""
        api_key = "plaintext-secret"
        expected_hash = hashlib.sha256(api_key.encode()).hexdigest()
        with patch("app.auth.auth_middleware.db") as mock_db:
            mock_db.get_agent_by_api_key_hash = AsyncMock(
                return_value={"agent_id": uuid4(), "principal_id": uuid4()}
            )
            await AuthMiddleware._verify_agent_key(api_key)
            mock_db.get_agent_by_api_key_hash.assert_awaited_once_with(expected_hash)

    async def test_unknown_key_raises_keyerror(self) -> None:
        with patch("app.auth.auth_middleware.db") as mock_db:
            mock_db.get_agent_by_api_key_hash = AsyncMock(return_value=None)
            with pytest.raises(KeyError):
                await AuthMiddleware._verify_agent_key("nope")


def _whoami_app() -> FastAPI:
    """AuthMiddleware 를 단 더미 앱 — request.state.auth 를 반환한다."""
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/v1/agents/whoami")
    async def whoami(request: Request) -> dict:  # noqa: WPS430
        ctx = request.state.auth
        return {"role": ctx.role, "agent_id": str(ctx.agent_id)}

    return app


class TestAgentKeyDispatch:
    """AuthMiddleware.dispatch 의 X-Agent-Key 분기 (실제 미들웨어 경유)."""

    async def test_valid_header_authenticates_as_agent(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        app = _whoami_app()
        with patch("app.auth.auth_middleware.db") as mock_db:
            mock_db.get_agent_by_api_key_hash = AsyncMock(
                return_value={"agent_id": agent_id, "principal_id": principal_id}
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/v1/agents/whoami", headers={"X-Agent-Key": "valid-key"}
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == "agent"
        assert body["agent_id"] == str(agent_id)

    async def test_invalid_header_returns_401(self) -> None:
        app = _whoami_app()
        with patch("app.auth.auth_middleware.db") as mock_db:
            mock_db.get_agent_by_api_key_hash = AsyncMock(return_value=None)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    "/v1/agents/whoami", headers={"X-Agent-Key": "bad-key"}
                )

        assert resp.status_code == 401

    async def test_no_credentials_returns_401(self) -> None:
        """X-Agent-Key 도 Bearer 도 없으면 기존 동작대로 401."""
        app = _whoami_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/v1/agents/whoami")

        assert resp.status_code == 401
