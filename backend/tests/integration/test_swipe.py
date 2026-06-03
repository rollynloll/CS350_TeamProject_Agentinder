"""
test_swipe.py — swipe 핸들러 상호 매치 감지 로직 통합 테스트.

테스트 대상: backend/app/handlers/feed_handler.py::swipe
호출 위치: pytest 수집 시 자동 실행.

DB 호출(db.insert_swipe, db.get_counter_swipe, db.insert_match,
         db.get_agent_row)과 EventBus는 모두 mock으로 처리한다.
FastAPI TestClient 대신 httpx.AsyncClient + ASGITransport 를 사용한다.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.auth_context import AuthContext
from app.handlers.feed_handler import router
from app.pubsub.event_bus import EventBus


# ── 헬퍼 ─────────────────────────────────────────────────────────────────

def make_agent_row(agent_id: UUID, principal_id: UUID) -> dict:
    """asyncpg.Record 대신 dict-like 객체를 반환한다.

    필드 구조:
      agent_id: UUID
      principal_id: UUID
      display_name: str
      visibility: str  ("public" | "restricted" | "hidden")
      trust_score: float
      tier_badge: str
      date_count: int
      avatar_url: None
      has_embedding: bool
    """
    return {
        "agent_id": agent_id,
        "principal_id": principal_id,
        "display_name": "Test Agent",
        "visibility": "public",
        "trust_score": 0.8,
        "tier_badge": "gold",
        "date_count": 3,
        "avatar_url": None,
        "has_embedding": True,
    }


def make_match_row(match_id: UUID) -> dict:
    """match_id 필드를 포함한 매치 레코드 mock."""
    return {"match_id": match_id}


def build_app(
    agent_id: UUID,
    principal_id: UUID,
    *,
    event_bus: EventBus | None = None,
    auth_ctx: AuthContext | None = None,
) -> FastAPI:
    """테스트용 FastAPI 앱을 구성한다.

    auth_ctx 미지정 시 소유자 principal 인증 컨텍스트를 주입한다.
    에이전트(X-Agent-Key) 인증 케이스는 auth_ctx 로 role="agent" 컨텍스트를 전달한다.
    """
    app = FastAPI()
    app.include_router(router)

    fake_principal = MagicMock()
    fake_principal.principal_id = principal_id

    ctx = auth_ctx or AuthContext(
        role="principal", session_id=principal_id, principal_id=principal_id
    )

    from app.deps import get_auth, get_event_bus, get_principal
    app.dependency_overrides[get_principal] = lambda: fake_principal
    app.dependency_overrides[get_event_bus] = lambda: event_bus or EventBus()
    app.dependency_overrides[get_auth] = lambda: ctx

    return app


class TestSwipeNoMatch:
    """스와이프만 하고 매치가 발생하지 않는 경우."""

    async def test_swipe_right_no_counter_returns_no_match(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()

        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, principal_id)
            )
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock(return_value=None)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "right"},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["swiped"] is True
        assert body["data"]["match"] is None

    async def test_swipe_left_skips_counter_check(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()

        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, principal_id)
            )
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "left"},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["match"] is None
        # left 스와이프는 카운터 체크 자체를 하지 않아야 한다
        mock_db.get_counter_swipe.assert_not_called()


class TestSwipeWithMutualMatch:
    """상호 스와이프로 매치가 생성되는 경우."""

    async def test_swipe_right_mutual_creates_match(self) -> None:
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()
        target_principal_id = uuid4()
        match_id = uuid4()

        bus = EventBus()
        app = build_app(agent_id, principal_id, event_bus=bus)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(side_effect=lambda aid: (
                make_agent_row(agent_id, principal_id)
                if aid == agent_id
                else make_agent_row(target_id, target_principal_id)
            ))
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock(
                return_value={"id": uuid4()}  # 카운터 스와이프 존재
            )
            mock_db.insert_match = AsyncMock(return_value=make_match_row(match_id))

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "right"},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["swiped"] is True
        assert body["data"]["match"] is not None
        assert body["data"]["match"]["match_id"] == str(match_id)

    async def test_swipe_up_mutual_creates_match(self) -> None:
        """direction=up 도 상호 매치를 감지해야 한다."""
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()
        target_principal_id = uuid4()
        match_id = uuid4()

        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(side_effect=lambda aid: (
                make_agent_row(agent_id, principal_id)
                if aid == agent_id
                else make_agent_row(target_id, target_principal_id)
            ))
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock(return_value={"id": uuid4()})
            mock_db.insert_match = AsyncMock(return_value=make_match_row(match_id))

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "up"},
                )

        assert resp.status_code == 200
        assert resp.json()["data"]["match"]["match_id"] == str(match_id)

    async def test_swipe_match_publishes_match_created_event(self) -> None:
        """매치 생성 시 EventBus에 MatchCreated 이벤트가 발행된다."""
        import asyncio

        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()
        target_principal_id = uuid4()
        match_id = uuid4()

        bus = EventBus()
        captured: list = []

        async def on_match(event) -> None:
            captured.append(event)

        bus.subscribe("MatchCreated", on_match)
        app = build_app(agent_id, principal_id, event_bus=bus)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(side_effect=lambda aid: (
                make_agent_row(agent_id, principal_id)
                if aid == agent_id
                else make_agent_row(target_id, target_principal_id)
            ))
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock(return_value={"id": uuid4()})
            mock_db.insert_match = AsyncMock(return_value=make_match_row(match_id))

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "right"},
                )

            await asyncio.sleep(0)

        assert len(captured) == 1
        from app.pubsub.domain_events import MatchCreated
        assert isinstance(captured[0], MatchCreated)
        assert captured[0].match_id == match_id

    async def test_swipe_match_already_exists_returns_no_match(self) -> None:
        """insert_match가 None 반환 시(이미 존재) match 필드가 None."""
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()
        target_principal_id = uuid4()

        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(side_effect=lambda aid: (
                make_agent_row(agent_id, principal_id)
                if aid == agent_id
                else make_agent_row(target_id, target_principal_id)
            ))
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock(return_value={"id": uuid4()})
            mock_db.insert_match = AsyncMock(return_value=None)  # 이미 존재

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "right"},
                )

        assert resp.status_code == 200
        assert resp.json()["data"]["match"] is None

    async def test_swipe_match_sorts_agent_ids_deterministically(self) -> None:
        """insert_match는 sorted([agent_id, target_id]) 순서로 호출된다."""
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()
        target_principal_id = uuid4()
        match_id = uuid4()

        app = build_app(agent_id, principal_id)
        a, b = sorted([agent_id, target_id], key=str)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(side_effect=lambda aid: (
                make_agent_row(agent_id, principal_id)
                if aid == agent_id
                else make_agent_row(target_id, target_principal_id)
            ))
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock(return_value={"id": uuid4()})
            mock_db.insert_match = AsyncMock(return_value=make_match_row(match_id))

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "right"},
                )

        mock_db.insert_match.assert_awaited_once_with(a, b)


class TestSwipeValidation:
    """입력 검증 테스트."""

    async def test_invalid_direction_raises_value_error(self) -> None:
        """direction 유효성 검사 실패 시 핸들러가 ValueError를 발생시킨다.

        ErrorHandlerMiddleware 없는 테스트 앱에서는 서버 예외가
        ASGI 레벨로 올라오므로 pytest.raises 로 검증한다.
        """
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()

        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, principal_id)
            )
            mock_db.insert_swipe = AsyncMock()

            with pytest.raises(ValueError, match="유효하지 않은 direction"):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    await client.post(
                        f"/v1/agents/{agent_id}/swipe",
                        json={"target_id": str(target_id), "direction": "INVALID"},
                    )

    async def test_agent_not_found_raises_key_error(self) -> None:
        """에이전트를 찾을 수 없을 때 핸들러가 KeyError를 발생시킨다.

        ErrorHandlerMiddleware 없는 테스트 앱에서는 서버 예외가
        ASGI 레벨로 올라오므로 pytest.raises 로 검증한다.
        """
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()

        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(return_value=None)

            with pytest.raises(KeyError):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    await client.post(
                        f"/v1/agents/{agent_id}/swipe",
                        json={"target_id": str(target_id), "direction": "right"},
                    )

    async def test_swipe_direction_normalized_to_lowercase(self) -> None:
        """direction 값은 소문자로 정규화된 후 검증된다."""
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()

        app = build_app(agent_id, principal_id)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, principal_id)
            )
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock(return_value=None)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "RIGHT"},
                )

        # "RIGHT".lower() = "right" → 정상 처리
        assert resp.status_code == 200


class TestSwipeAgentAuth:
    """X-Agent-Key(role="agent") 인증으로 스와이프하는 경우의 권한 검사."""

    async def test_agent_can_swipe_with_own_agent_id(self) -> None:
        """에이전트는 자기 자신(agent_id)으로 스와이프할 수 있다."""
        agent_id = uuid4()
        principal_id = uuid4()
        target_id = uuid4()

        agent_ctx = AuthContext(
            role="agent", session_id=agent_id, agent_id=agent_id, principal_id=principal_id
        )
        app = build_app(agent_id, principal_id, auth_ctx=agent_ctx)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, principal_id)
            )
            mock_db.insert_swipe = AsyncMock()
            mock_db.get_counter_swipe = AsyncMock(return_value=None)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/v1/agents/{agent_id}/swipe",
                    json={"target_id": str(target_id), "direction": "right"},
                )

        assert resp.status_code == 200
        assert resp.json()["data"]["swiped"] is True

    async def test_agent_cannot_swipe_as_other_agent(self) -> None:
        """다른 에이전트 id 로는 스와이프할 수 없다 (PermissionError)."""
        agent_id = uuid4()        # path 의 대상 에이전트
        other_agent_id = uuid4()  # 인증된 에이전트(본인)
        principal_id = uuid4()
        target_id = uuid4()

        # 인증 주체는 other_agent_id 인데 path 는 agent_id → 거부되어야 함
        agent_ctx = AuthContext(
            role="agent", session_id=other_agent_id,
            agent_id=other_agent_id, principal_id=principal_id,
        )
        app = build_app(agent_id, principal_id, auth_ctx=agent_ctx)

        with patch("app.handlers.feed_handler.db") as mock_db:
            mock_db.get_agent_row = AsyncMock(
                return_value=make_agent_row(agent_id, principal_id)
            )
            mock_db.insert_swipe = AsyncMock()

            with pytest.raises(PermissionError):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    await client.post(
                        f"/v1/agents/{agent_id}/swipe",
                        json={"target_id": str(target_id), "direction": "right"},
                    )
