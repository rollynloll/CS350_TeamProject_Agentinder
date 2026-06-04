"""
시나리오 1 — 온보딩.

흐름: 로그인 직후 회원 생성(POST /v1/principals) → 첫 에이전트 생성(POST /v1/agents).
깊이: 핸들러 통합 (DB는 AsyncMock).

검증 포인트:
  - principals 레코드 멱등 생성, envelope.data 형태
  - createAgent 위임 + api_key 1회 노출
  - DB insert 호출됨
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.handlers import agent_profile_handler, principal_handler

from ._scenario_helpers import (
    build_app,
    make_agent_request,
    make_auth_ctx,
    make_principal,
    make_principal_row,
)


class TestOnboarding:
    async def test_create_principal_returns_envelope(self) -> None:
        pid = uuid4()
        auth = make_auth_ctx(pid, email="newuser@example.com")
        app = build_app(principal_handler.router, auth_ctx=auth)

        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(
                return_value=make_principal_row(pid, email="newuser@example.com", name="newuser")
            )
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/principals", json={})

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["principal_id"] == str(pid)
        assert data["email"] == "newuser@example.com"
        assert data["plan"].isupper()  # FREE | PREMIUM

    async def test_create_first_agent_after_signup(self) -> None:
        principal = make_principal()
        app = build_app(agent_profile_handler.router, principal=principal)

        with patch("app.handlers.agent_profile_handler.db") as mock_db:
            mock_db.insert_agent_full = AsyncMock()
            mock_db.sync_capability_tags = AsyncMock()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/agents", json=make_agent_request("First Agent"))

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["display_name"] == "First Agent"
        assert data["api_key"]  # 1회 노출
        assert data["principal_id"] == str(principal.principal_id)
        mock_db.insert_agent_full.assert_awaited_once()

    async def test_onboarding_chain_principal_then_agent(self) -> None:
        """회원 생성 → 같은 principal로 에이전트 생성까지 연결."""
        pid = uuid4()
        # step 1: principal
        auth = make_auth_ctx(pid)
        app1 = build_app(principal_handler.router, auth_ctx=auth)
        with patch("app.handlers.principal_handler.db") as mock_db:
            mock_db.upsert_principal = AsyncMock(return_value=make_principal_row(pid))
            async with AsyncClient(transport=ASGITransport(app=app1), base_url="http://test") as c:
                r1 = await c.post("/v1/principals", json={})
        assert r1.json()["data"]["principal_id"] == str(pid)

        # step 2: agent under that principal
        principal = make_principal(principal_id=pid)
        app2 = build_app(agent_profile_handler.router, principal=principal)
        with patch("app.handlers.agent_profile_handler.db") as mock_db:
            mock_db.insert_agent_full = AsyncMock()
            mock_db.sync_capability_tags = AsyncMock()
            async with AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as c:
                r2 = await c.post("/v1/agents", json=make_agent_request())
        assert r2.json()["data"]["principal_id"] == str(pid)
