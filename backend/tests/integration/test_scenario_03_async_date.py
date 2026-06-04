"""
시나리오 3 — 비동기 데이트.

흐름: 매치 참여자가 예약형(비라이브) 데이트 제안(POST /v1/matches/{id}/dates)
      → scheduled_at 지정 → DateProposed 이벤트 발행 → 조회(GET /v1/dates/{id}).
깊이: 핸들러 통합 (DB는 AsyncMock).

NOTE: propose_date / get_date 는 인가 검사로 authorization_policy.db 도 호출 →
      date_handler.db 와 authorization_policy.db 둘 다 패치해야 한다.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.handlers import date_handler
from app.pubsub.domain_events import DateProposed
from app.pubsub.event_bus import EventBus

from ._scenario_helpers import (
    build_app,
    make_agent_row,
    make_auth_ctx,
    make_date_row,
    make_match_row,
    make_principal,
)


class TestAsyncDate:
    async def test_propose_scheduled_date(self) -> None:
        principal = make_principal()
        ctx = make_auth_ctx(principal.principal_id)
        match_id, date_id = uuid4(), uuid4()
        agent_a, agent_b = uuid4(), uuid4()
        other_pid = uuid4()
        scheduled = datetime(2026, 7, 1, 15, 0, tzinfo=timezone.utc)

        bus = EventBus()
        captured: list = []
        bus.subscribe("DateProposed", lambda e: captured.append(e))

        app = build_app(date_handler.router, principal=principal, auth_ctx=ctx, event_bus=bus)

        match_row = make_match_row(match_id, agent_a, agent_b)
        date_row = make_date_row(date_id, match_id, type="async", scheduled_at=scheduled)

        def agent_row_side(aid):
            # agent_a 는 내 소유, agent_b 는 상대 소유
            pid = principal.principal_id if aid == agent_a else other_pid
            return make_agent_row(aid, pid)

        with patch("app.handlers.date_handler.db") as mock_db, \
             patch("app.auth.authorization_policy.db") as mock_authdb:
            mock_authdb.get_match = AsyncMock(return_value=match_row)
            mock_authdb.get_agent_row = AsyncMock(side_effect=agent_row_side)
            mock_db.get_match = AsyncMock(return_value=match_row)
            mock_db.get_agent_row = AsyncMock(side_effect=agent_row_side)
            mock_db.insert_date = AsyncMock(return_value=date_row)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    f"/v1/matches/{match_id}/dates",
                    json={"type": "async", "scheduled_at": scheduled.isoformat()},
                )
            await asyncio.sleep(0)

        assert resp.status_code == 200
        assert resp.json()["data"]["date_id"] == str(date_id)
        mock_db.insert_date.assert_awaited_once()
        # DateProposed 발행 검증
        assert len(captured) == 1
        assert isinstance(captured[0], DateProposed)
        assert captured[0].target_principal_id == other_pid

    async def test_get_date(self) -> None:
        principal = make_principal()
        ctx = make_auth_ctx(principal.principal_id)
        match_id, date_id = uuid4(), uuid4()
        agent_a, agent_b = uuid4(), uuid4()
        match_row = make_match_row(match_id, agent_a, agent_b)
        date_row = make_date_row(date_id, match_id, type="async")

        app = build_app(date_handler.router, principal=principal, auth_ctx=ctx)

        def agent_row_side(aid):
            return make_agent_row(aid, principal.principal_id)

        with patch("app.handlers.date_handler.db") as mock_db, \
             patch("app.auth.authorization_policy.db") as mock_authdb:
            mock_authdb.get_date = AsyncMock(return_value=date_row)
            mock_authdb.get_match = AsyncMock(return_value=match_row)
            mock_authdb.get_agent_row = AsyncMock(side_effect=agent_row_side)
            mock_db.get_date = AsyncMock(return_value=date_row)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(f"/v1/dates/{date_id}")

        assert resp.status_code == 200
        assert resp.json()["data"]["date_id"] == str(date_id)

    async def test_propose_rejects_non_participant(self) -> None:
        """매치 참여자가 아니면 PermissionError."""
        import pytest
        principal = make_principal()
        ctx = make_auth_ctx(principal.principal_id)
        match_id = uuid4()
        agent_a, agent_b = uuid4(), uuid4()
        outsider_pid = uuid4()  # 두 agent 모두 남의 것
        match_row = make_match_row(match_id, agent_a, agent_b)

        app = build_app(date_handler.router, principal=principal, auth_ctx=ctx)

        with patch("app.handlers.date_handler.db") as mock_db, \
             patch("app.auth.authorization_policy.db") as mock_authdb:
            mock_authdb.get_match = AsyncMock(return_value=match_row)
            mock_authdb.get_agent_row = AsyncMock(
                side_effect=lambda aid: make_agent_row(aid, outsider_pid)
            )
            with pytest.raises(PermissionError):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    await c.post(f"/v1/matches/{match_id}/dates", json={"type": "async"})
