"""
시나리오 6 — 탐색 동기 데이트.

흐름: 탐색(피드)으로 후보 발견 → 데이트 제안 → 양측 join_date(WS) →
      DateStarted(라이브 시작) → end_date + 평가 → trust 반영.
깊이: 핸들러 통합. WS join_date 는 date_handler.handle_join_date 직접 호출
      (ws_transport._dispatch 가 위임하는 동일 함수).

NOTE: '동기' = 라이브(양측 동시 접속) 데이트. '비동기'(시나리오 3)와 대비.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app import deps
from app.handlers import date_handler
from app.pubsub.domain_events import DateStarted
from app.pubsub.event_bus import EventBus

from ._scenario_helpers import (
    build_app,
    make_agent_request,
    make_agent_row,
    make_auth_ctx,
    make_date_row,
    make_match_row,
    make_principal,
)


@pytest.fixture(autouse=True)
def _clear_pending_joins():
    """date_handler 모듈 전역 _pending_joins 초기화."""
    date_handler._pending_joins.clear()
    yield
    date_handler._pending_joins.clear()


def _principal_with_two_agents():
    principal = make_principal()
    a, _ = principal.createAgent(make_agent_request("Agent A"))
    b, _ = principal.createAgent(make_agent_request("Agent B"))
    return principal, a.agent_id, b.agent_id


class TestSyncDateLifecycle:
    async def test_first_join_waits_second_starts(self) -> None:
        """첫 참여자 join → started=False, 둘째 join → DateStarted 발행."""
        principal, agent_a, agent_b = _principal_with_two_agents()
        match_id, date_id = uuid4(), uuid4()
        date_row = make_date_row(date_id, match_id, type="sync")

        bus = EventBus()
        started: list = []
        bus.subscribe("DateStarted", lambda e: started.append(e))

        with patch("app.handlers.date_handler.db") as mock_db:
            mock_db.get_date = AsyncMock(return_value=date_row)
            mock_db.start_date = AsyncMock()

            r1 = await date_handler.handle_join_date(date_id, agent_a, principal, bus)
            assert r1 == {"joined": True, "started": False}
            assert started == []

            r2 = await date_handler.handle_join_date(date_id, agent_b, principal, bus)
            await asyncio.sleep(0)
            assert r2 == {"joined": True, "started": True}
            mock_db.start_date.assert_awaited_once_with(date_id)

        assert len(started) == 1
        assert isinstance(started[0], DateStarted)
        assert started[0].date_id == date_id

    async def test_full_sync_date_end_records_trust(self) -> None:
        """join x2 → end_date + 평가 → recordSuccessfulDate/checkUpgrade 호출."""
        principal, agent_a, agent_b = _principal_with_two_agents()
        ctx = make_auth_ctx(principal.principal_id)
        match_id, date_id = uuid4(), uuid4()
        date_row = make_date_row(date_id, match_id, type="sync")
        match_row = make_match_row(match_id, agent_a, agent_b)

        bus = EventBus()
        # end_date 핸들러는 deps.score_manager 싱글톤을 사용 → principal의 것으로 주입
        sm = principal._score_manager

        app = build_app(date_handler.router, principal=principal, auth_ctx=ctx, event_bus=bus)

        def agent_row_side(aid):
            return make_agent_row(aid, principal.principal_id)

        with patch("app.handlers.date_handler.db") as mock_db, \
             patch("app.auth.authorization_policy.db") as mock_authdb, \
             patch.object(deps, "score_manager", sm), \
             patch.object(deps, "agent_service", principal._agent_service):
            mock_db.get_date = AsyncMock(return_value=date_row)
            mock_db.start_date = AsyncMock()
            mock_db.get_match = AsyncMock(return_value=match_row)
            mock_db.end_date = AsyncMock()
            mock_authdb.get_date = AsyncMock(return_value=date_row)
            mock_authdb.get_match = AsyncMock(return_value=match_row)
            mock_authdb.get_agent_row = AsyncMock(side_effect=agent_row_side)

            # 양측 라이브 입장
            await date_handler.handle_join_date(date_id, agent_a, principal, bus)
            await date_handler.handle_join_date(date_id, agent_b, principal, bus)

            with patch.object(sm, "recordSuccessfulDate", wraps=sm.recordSuccessfulDate) as rec, \
                 patch.object(sm, "checkUpgrade", wraps=sm.checkUpgrade) as chk:
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    resp = await c.post(
                        f"/v1/dates/{date_id}/end",
                        json={
                            "outcome": "success",
                            "rating_stars": 5,
                            "rating_compatibility": 0.9,
                            "rated_agent_id": str(agent_b),
                        },
                    )

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "success"
        rec.assert_called_once()
        chk.assert_called_once()
        mock_db.end_date.assert_awaited_once()
