"""
test_ws_gateway.py — WSGateway 토픽 구독/해제/push 단위 테스트.

테스트 대상: backend/app/gateway/ws_gateway.py
호출 위치: pytest 수집 시 자동 실행.

WSGateway가 settings를 임포트하므로 conftest.py에서 env 세팅이 선행됨.
WebSocket 의존성은 MagicMock으로 대체한다.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.gateway.ws_gateway import WSGateway
from app.pubsub.domain_events import (
    DateEnded,
    DateProposed,
    DateStarted,
    MatchCreated,
    MessageCreated,
)


def make_mock_ws() -> MagicMock:
    """send_text를 AsyncMock으로 갖는 WebSocket 목을 반환한다."""
    ws = MagicMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    ws.accept = AsyncMock()
    return ws


class TestWSGatewayTopicSubscription:
    """토픽 구독 및 해제 기본 동작 테스트."""

    def test_subscribe_topic_registers_ws(self) -> None:
        gw = WSGateway()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, "matches.test-id")
        assert ws in gw._topics["matches.test-id"]

    def test_subscribe_multiple_ws_to_same_topic(self) -> None:
        gw = WSGateway()
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        gw.subscribe_topic(ws1, "chat.match-123")
        gw.subscribe_topic(ws2, "chat.match-123")
        assert ws1 in gw._topics["chat.match-123"]
        assert ws2 in gw._topics["chat.match-123"]

    def test_subscribe_same_ws_to_multiple_topics(self) -> None:
        gw = WSGateway()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, "matches.pid-1")
        gw.subscribe_topic(ws, "notifications.pid-1")
        assert ws in gw._topics["matches.pid-1"]
        assert ws in gw._topics["notifications.pid-1"]

    def test_unsubscribe_topic_removes_ws(self) -> None:
        gw = WSGateway()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, "matches.test")
        gw.unsubscribe_topic(ws, "matches.test")
        assert ws not in gw._topics["matches.test"]

    def test_unsubscribe_nonexistent_topic_does_not_raise(self) -> None:
        gw = WSGateway()
        ws = make_mock_ws()
        gw.unsubscribe_topic(ws, "nonexistent.topic")

    def test_unsubscribe_only_removes_target_ws(self) -> None:
        gw = WSGateway()
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        gw.subscribe_topic(ws1, "chat.mid")
        gw.subscribe_topic(ws2, "chat.mid")
        gw.unsubscribe_topic(ws1, "chat.mid")
        assert ws1 not in gw._topics["chat.mid"]
        assert ws2 in gw._topics["chat.mid"]


class TestWSGatewayPushToTopic:
    """push_to_topic — 구독자에게 메시지 전송 테스트."""

    async def test_push_to_topic_sends_json_to_subscriber(self) -> None:
        gw = WSGateway()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, "chat.match-1")
        event = {"event": "message", "content": "hi"}
        await gw.push_to_topic("chat.match-1", event)
        ws.send_text.assert_awaited_once_with(json.dumps(event))

    async def test_push_to_topic_sends_to_all_subscribers(self) -> None:
        gw = WSGateway()
        ws1 = make_mock_ws()
        ws2 = make_mock_ws()
        gw.subscribe_topic(ws1, "chat.match-2")
        gw.subscribe_topic(ws2, "chat.match-2")
        event = {"event": "message", "content": "hello"}
        await gw.push_to_topic("chat.match-2", event)
        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()

    async def test_push_to_topic_no_subscribers_does_nothing(self) -> None:
        gw = WSGateway()
        # 예외 없이 통과해야 한다
        await gw.push_to_topic("chat.nobody", {"event": "test"})

    async def test_push_to_topic_removes_dead_connections(self) -> None:
        """send_text 실패 시 해당 ws를 토픽에서 제거한다."""
        gw = WSGateway()
        ws = make_mock_ws()
        ws.send_text.side_effect = RuntimeError("연결 끊김")
        gw.subscribe_topic(ws, "chat.dead")
        await gw.push_to_topic("chat.dead", {"event": "test"})
        assert ws not in gw._topics.get("chat.dead", set())

    async def test_push_to_topic_only_sends_to_matching_topic(self) -> None:
        gw = WSGateway()
        ws_a = make_mock_ws()
        ws_b = make_mock_ws()
        gw.subscribe_topic(ws_a, "chat.match-a")
        gw.subscribe_topic(ws_b, "chat.match-b")
        await gw.push_to_topic("chat.match-a", {"event": "msg"})
        ws_a.send_text.assert_awaited_once()
        ws_b.send_text.assert_not_called()


class TestWSGatewayOnDisconnect:
    """on_disconnect — 연결 해제 시 모든 토픽에서 제거 테스트."""

    async def test_on_disconnect_removes_ws_from_all_topics(self) -> None:
        gw = WSGateway()
        pid = uuid4()
        ws = make_mock_ws()
        gw._connections[pid].add(ws)
        gw.subscribe_topic(ws, "chat.m1")
        gw.subscribe_topic(ws, "matches.p1")
        await gw.on_disconnect(ws, pid)
        assert ws not in gw._topics.get("chat.m1", set())
        assert ws not in gw._topics.get("matches.p1", set())

    async def test_on_disconnect_removes_from_connection_registry(self) -> None:
        gw = WSGateway()
        pid = uuid4()
        ws = make_mock_ws()
        gw._connections[pid].add(ws)
        await gw.on_disconnect(ws, pid)
        assert ws not in gw._connections[pid]


class TestWSGatewayOnDomainEvent:
    """on_domain_event — DomainEvent 종류별 토픽 push 라우팅 테스트."""

    async def test_match_created_pushes_to_principal_a_topic(self) -> None:
        gw = WSGateway()
        pa_id = uuid4()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, f"matches.{pa_id}")
        mid = uuid4()
        ev = MatchCreated(match_id=mid, principal_a_id=pa_id)
        await gw.on_domain_event(ev)
        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["event"] == "new_match"
        assert sent["match_id"] == str(mid)

    async def test_match_created_pushes_to_principal_b_topic(self) -> None:
        gw = WSGateway()
        pb_id = uuid4()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, f"matches.{pb_id}")
        ev = MatchCreated(principal_b_id=pb_id)
        await gw.on_domain_event(ev)
        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["event"] == "new_match"

    async def test_match_created_no_push_when_no_principal_ids(self) -> None:
        gw = WSGateway()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, "matches.whatever")
        ev = MatchCreated(principal_a_id=None, principal_b_id=None)
        await gw.on_domain_event(ev)
        ws.send_text.assert_not_called()

    async def test_date_proposed_pushes_to_target_notifications(self) -> None:
        gw = WSGateway()
        target_pid = uuid4()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, f"notifications.{target_pid}")
        did = uuid4()
        ev = DateProposed(date_id=did, target_principal_id=target_pid)
        await gw.on_domain_event(ev)
        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["event"] == "date_proposed"
        assert sent["date_id"] == str(did)

    async def test_date_started_pushes_to_date_topic(self) -> None:
        gw = WSGateway()
        did = uuid4()
        mid = uuid4()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, f"date.{did}")
        ev = DateStarted(date_id=did, match_id=mid)
        await gw.on_domain_event(ev)
        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["event"] == "date_started"

    async def test_date_ended_pushes_to_date_topic(self) -> None:
        gw = WSGateway()
        did = uuid4()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, f"date.{did}")
        ev = DateEnded(date_id=did, outcome="success")
        await gw.on_domain_event(ev)
        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["event"] == "date_ended"
        assert sent["outcome"] == "success"

    async def test_message_created_pushes_to_chat_topic(self) -> None:
        gw = WSGateway()
        mid = uuid4()
        sender = uuid4()
        msg_id = uuid4()
        ws = make_mock_ws()
        gw.subscribe_topic(ws, f"chat.{mid}")
        ev = MessageCreated(message_id=msg_id, match_id=mid, sender_agent_id=sender, content="hi")
        await gw.on_domain_event(ev)
        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["event"] == "message"
        assert sent["content"] == "hi"
        assert sent["sender_agent_id"] == str(sender)


class TestWSGatewayOnConnect:
    """on_connect — JWT 검증 및 연결 등록 테스트."""

    async def test_on_connect_rejects_invalid_token(self) -> None:
        gw = WSGateway()
        ws = make_mock_ws()
        result = await gw.on_connect(ws, "not-a-valid-jwt")
        assert result is None
        ws.close.assert_awaited_once_with(code=4001)

    async def test_on_connect_accepts_valid_token(self) -> None:
        from jose import jwt as jose_jwt
        pid = uuid4()
        secret = "fake-jwt-secret-for-testing-only"
        token = jose_jwt.encode({"sub": str(pid)}, secret, algorithm="HS256")
        gw = WSGateway()
        ws = make_mock_ws()

        # settings.supabase_jwt_secret 을 fake secret 으로 패치
        with patch("app.gateway.ws_gateway.settings") as mock_settings:
            mock_settings.supabase_jwt_secret = secret
            result = await gw.on_connect(ws, token)

        assert result == pid
        ws.accept.assert_awaited_once()
        assert ws in gw._connections[pid]
