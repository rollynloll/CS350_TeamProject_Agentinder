"""
시나리오 2 — 에이전트 CRUD.

흐름: 생성(POST) → 조회(GET) → 수정(PATCH) → 목록(GET /).
깊이: 핸들러 통합 (DB는 AsyncMock).

NOTE: DELETE /v1/agents/{id} 핸들러는 현재 미구현 (README엔 명세됨).
      test_delete_not_implemented 가 그 갭을 표시한다.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.handlers import agent_profile_handler

from ._scenario_helpers import (
    build_app,
    make_agent_request,
    make_agent_row,
    make_principal,
)


def _create_agent_on(principal):
    """핸들러 우회로 principal에 에이전트 1개 심고 agent_id 반환."""
    agent, _ = principal.createAgent(make_agent_request("Seed Agent"))
    return agent.agent_id


class TestAgentCrud:
    async def test_create_agent(self) -> None:
        principal = make_principal()
        app = build_app(agent_profile_handler.router, principal=principal)
        with patch("app.handlers.agent_profile_handler.db") as mock_db:
            mock_db.insert_agent_full = AsyncMock()
            mock_db.sync_capability_tags = AsyncMock()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/v1/agents", json=make_agent_request("CRUD Agent"))
        assert resp.status_code == 200
        assert resp.json()["data"]["display_name"] == "CRUD Agent"

    async def test_get_profile(self) -> None:
        agent_id = uuid4()
        principal = make_principal()
        app = build_app(agent_profile_handler.router, principal=principal)
        with patch("app.handlers.agent_profile_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, principal.principal_id)
            )
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(f"/v1/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["agent_id"] == str(agent_id)

    async def test_get_profile_not_found(self) -> None:
        principal = make_principal()
        app = build_app(agent_profile_handler.router, principal=principal)
        with patch("app.handlers.agent_profile_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(return_value=None)
            with pytest.raises(KeyError):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    await c.get(f"/v1/agents/{uuid4()}")

    async def test_update_agent(self) -> None:
        principal = make_principal()
        agent_id = _create_agent_on(principal)  # agent_service에 등록됨
        app = build_app(agent_profile_handler.router, principal=principal)
        with patch("app.handlers.agent_profile_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, principal.principal_id)
            )
            mock_db.upsert_agent_profile_row = AsyncMock()
            mock_db.sync_capability_tags = AsyncMock()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.patch(
                    f"/v1/agents/{agent_id}",
                    json={"display_name": "Renamed Agent"},
                )
        assert resp.status_code == 200
        assert resp.json()["data"]["display_name"] == "Renamed Agent"
        mock_db.upsert_agent_profile_row.assert_awaited_once()

    async def test_update_rejects_non_owner(self) -> None:
        principal = make_principal()
        agent_id = uuid4()
        other_principal_id = uuid4()
        app = build_app(agent_profile_handler.router, principal=principal)
        with patch("app.handlers.agent_profile_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, other_principal_id)
            )
            with pytest.raises(PermissionError):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    await c.patch(f"/v1/agents/{agent_id}", json={"display_name": "X"})

    async def test_list_agents(self) -> None:
        principal = make_principal()
        a1, a2 = uuid4(), uuid4()
        app = build_app(agent_profile_handler.router, principal=principal)
        with patch("app.handlers.agent_profile_handler.db") as mock_db:
            mock_db.get_principal_agents = AsyncMock(return_value=[
                make_agent_row(a1, principal.principal_id),
                make_agent_row(a2, principal.principal_id),
            ])
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/v1/agents")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_delete_not_implemented(self) -> None:
        """DELETE 라우트 부재 확인 — 구현되면 이 테스트를 실제 검증으로 교체."""
        routes = {(r.path, m) for r in agent_profile_handler.router.routes
                  for m in getattr(r, "methods", set())}
        assert ("/v1/agents/{agent_id}", "DELETE") not in routes, \
            "DELETE 구현됨 → 이 시나리오를 실제 삭제 테스트로 교체하세요."
