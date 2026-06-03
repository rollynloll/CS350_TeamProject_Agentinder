"""
test_discover.py — Discover(필터 검색) 엔드포인트 통합 테스트.

테스트 대상: backend/app/handlers/feed_handler.py::discover
호출 위치: pytest 수집 시 자동 실행.

DB(db.get_agent_row, db.get_pool, db.get_agents_by_filters)와
deps.score_manager 는 mock 으로 처리한다.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.auth_context import AuthContext
from app.handlers.feed_handler import _paginate, router


# ── _paginate 단위 테스트 (cursor 중복 방지 회귀) ─────────────────────────

class TestPaginate:
    def _rows(self, n):
        # compatibility 내림차순으로 이미 정렬될 값
        return [{"agent_id": f"id-{i}", "compatibility_total": 1.0 - i * 0.01} for i in range(n)]

    def test_first_page_sets_next_cursor(self) -> None:
        page, next_cursor = _paginate(self._rows(5), cursor=None, limit=2)
        assert [r["agent_id"] for r in page] == ["id-0", "id-1"]
        assert next_cursor == "id-1"  # 마지막 항목

    def test_cursor_starts_after_cursor_item_no_duplicate(self) -> None:
        rows = self._rows(5)
        # 1페이지 마지막이 id-1 이었다면, 2페이지는 id-2 부터 (id-1 중복 없음)
        page, next_cursor = _paginate(rows, cursor="id-1", limit=2)
        assert [r["agent_id"] for r in page] == ["id-2", "id-3"]
        assert next_cursor == "id-3"

    def test_last_page_has_no_next_cursor(self) -> None:
        page, next_cursor = _paginate(self._rows(4), cursor="id-1", limit=10)
        assert [r["agent_id"] for r in page] == ["id-2", "id-3"]
        assert next_cursor is None

    def test_unknown_cursor_returns_empty(self) -> None:
        page, next_cursor = _paginate(self._rows(3), cursor="missing", limit=2)
        assert page == []
        assert next_cursor is None


# ── 헬퍼 ─────────────────────────────────────────────────────────────────

def make_agent_row(agent_id: UUID, principal_id: UUID) -> dict:
    return {
        "agent_id": agent_id,
        "principal_id": principal_id,
        "display_name": "Viewer",
        "visibility": "public",
        "trust_score": 0.9,
        "tier_badge": "new_agent",
        "date_count": 0,
        "avatar_url": None,
    }


def make_candidate_row(cand_id: UUID) -> dict:
    return {
        "agent_id": cand_id,
        "principal_id": uuid4(),
        "display_name": "Candidate",
        "visibility": "public",
        "trust_score": 0.7,
        "tier_badge": "new_agent",
        "date_count": 0,
        "avatar_url": None,
        "style_vector": {},
        "capability_tags": ["research"],
    }


def build_app(
    agent_id: UUID,
    principal_id: UUID,
    *,
    auth_ctx: AuthContext | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    fake_agent = MagicMock()
    fake_agent.agent_id = agent_id
    fake_agent.getTrustScore.return_value = 0.9

    fake_principal = MagicMock()
    fake_principal.principal_id = principal_id
    fake_principal.agents = [fake_agent]

    ctx = auth_ctx or AuthContext(
        role="principal", session_id=principal_id, principal_id=principal_id
    )

    from app.deps import get_auth, get_principal
    app.dependency_overrides[get_principal] = lambda: fake_principal
    app.dependency_overrides[get_auth] = lambda: ctx

    return app


def _setup_db(mock_db, agent_id, principal_id, candidates):
    mock_db.get_agent_row = AsyncMock(return_value=make_agent_row(agent_id, principal_id))
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[])  # already_swiped 없음
    mock_db.get_pool = MagicMock(return_value=pool)
    mock_db.get_agents_by_filters = AsyncMock(return_value=candidates)


class TestDiscoverFilters:
    """쿼리 파라미터가 db.get_agents_by_filters 로 정확히 전달되는지."""

    async def test_filters_forwarded_to_db(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db, \
             patch("app.handlers.feed_handler.deps") as mock_deps:
            _setup_db(mock_db, agent_id, principal_id, candidates=[])
            mock_deps.score_manager = MagicMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    f"/v1/agents/{agent_id}/discover",
                    params={
                        "capability": "research,coding",
                        "trustMin": 0.6,
                        "style": "verbose",
                    },
                )

        assert resp.status_code == 200
        mock_db.get_agents_by_filters.assert_awaited_once_with(
            agent_id,
            capability_tags=["research", "coding"],
            trust_min=0.6,
            trust_max=None,
            style="verbose",
            domain=None,
            availability=None,
            search_q=None,
        )

    async def test_no_filters_all_none(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db, \
             patch("app.handlers.feed_handler.deps") as mock_deps:
            _setup_db(mock_db, agent_id, principal_id, candidates=[])
            mock_deps.score_manager = MagicMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/v1/agents/{agent_id}/discover")

        assert resp.status_code == 200
        mock_db.get_agents_by_filters.assert_awaited_once_with(
            agent_id,
            capability_tags=None,
            trust_min=None,
            trust_max=None,
            style=None,
            domain=None,
            availability=None,
            search_q=None,
        )


class TestDiscoverResponse:
    """응답 구조: items / next_cursor / applied_filters."""

    async def test_response_contains_items_and_applied_filters(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        cand_id = uuid4()
        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db, \
             patch("app.handlers.feed_handler.deps") as mock_deps:
            _setup_db(
                mock_db, agent_id, principal_id, candidates=[make_candidate_row(cand_id)]
            )
            mock_deps.score_manager = MagicMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(
                    f"/v1/agents/{agent_id}/discover", params={"q": "research"}
                )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "next_cursor" in data
        assert data["applied_filters"] == {"q": "research"}
        assert len(data["items"]) == 1
        assert data["items"][0]["agent_id"] == str(cand_id)

    async def test_empty_result_returns_empty_items(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db, \
             patch("app.handlers.feed_handler.deps") as mock_deps:
            _setup_db(mock_db, agent_id, principal_id, candidates=[])
            mock_deps.score_manager = MagicMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/v1/agents/{agent_id}/discover")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["next_cursor"] is None


class TestDiscoverAuthorization:
    """principal / agent 인증 주체별 권한."""

    async def test_agent_can_discover_with_own_agent_id(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        agent_ctx = AuthContext(
            role="agent", session_id=agent_id,
            agent_id=agent_id, principal_id=principal_id,
        )
        app = build_app(agent_id, principal_id, auth_ctx=agent_ctx)

        with patch("app.handlers.feed_handler.db") as mock_db, \
             patch("app.handlers.feed_handler.deps") as mock_deps:
            _setup_db(mock_db, agent_id, principal_id, candidates=[])
            mock_deps.score_manager = MagicMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/v1/agents/{agent_id}/discover")

        assert resp.status_code == 200

    async def test_non_owner_principal_rejected(self) -> None:
        agent_id = uuid4()
        owner_principal_id = uuid4()
        other_principal_id = uuid4()
        # ctx 는 다른 principal — agent_row 의 소유자가 아님
        app = build_app(agent_id, other_principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db, \
             patch("app.handlers.feed_handler.deps") as mock_deps:
            # agent_row 의 소유자는 owner_principal_id
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, owner_principal_id)
            )
            mock_deps.score_manager = MagicMock()

            with pytest.raises(PermissionError):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    await client.get(f"/v1/agents/{agent_id}/discover")
