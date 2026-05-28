"""
test_event_bus.py — EventBus pub/sub 및 에러 격리 단위 테스트.

테스트 대상: backend/app/pubsub/event_bus.py
호출 위치: pytest 수집 시 자동 실행.
conftest.py의 event_bus fixture 사용.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.pubsub.domain_events import DomainEvent, MatchCreated, MessageCreated
from app.pubsub.event_bus import EventBus


class TestEventBusSubscribe:
    """subscribe/unsubscribe 기본 동작 테스트."""

    def test_subscribe_adds_handler(self) -> None:
        bus = EventBus()
        calls: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            calls.append(event)

        bus.subscribe("DomainEvent", handler)
        assert handler in bus._subscribers["DomainEvent"]

    def test_subscribe_multiple_handlers_for_same_event(self) -> None:
        bus = EventBus()

        async def h1(e: DomainEvent) -> None:
            pass

        async def h2(e: DomainEvent) -> None:
            pass

        bus.subscribe("MatchCreated", h1)
        bus.subscribe("MatchCreated", h2)
        assert len(bus._subscribers["MatchCreated"]) == 2

    def test_unsubscribe_removes_handler(self) -> None:
        bus = EventBus()

        async def handler(event: DomainEvent) -> None:
            pass

        bus.subscribe("MatchCreated", handler)
        bus.unsubscribe("MatchCreated", handler)
        assert handler not in bus._subscribers["MatchCreated"]

    def test_unsubscribe_nonexistent_handler_does_not_raise(self) -> None:
        bus = EventBus()

        async def handler(event: DomainEvent) -> None:
            pass

        bus.unsubscribe("MatchCreated", handler)  # 등록 안 한 상태에서 제거

    def test_unsubscribe_only_removes_target_handler(self) -> None:
        bus = EventBus()

        async def h1(e: DomainEvent) -> None:
            pass

        async def h2(e: DomainEvent) -> None:
            pass

        bus.subscribe("MatchCreated", h1)
        bus.subscribe("MatchCreated", h2)
        bus.unsubscribe("MatchCreated", h1)
        assert h1 not in bus._subscribers["MatchCreated"]
        assert h2 in bus._subscribers["MatchCreated"]


class TestEventBusPublish:
    """publish 후 핸들러 실행 테스트 (asyncio.run으로 태스크 완료 대기)."""

    async def test_publish_calls_subscribed_handler(self) -> None:
        bus = EventBus()
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe("MatchCreated", handler)
        ev = MatchCreated()
        bus.publish(ev)
        # asyncio.create_task 가 즉시 실행되지 않으므로 루프 양보
        await asyncio.sleep(0)
        assert len(received) == 1
        assert received[0] is ev

    async def test_publish_calls_multiple_handlers(self) -> None:
        bus = EventBus()
        log: list[str] = []

        async def h1(event: DomainEvent) -> None:
            log.append("h1")

        async def h2(event: DomainEvent) -> None:
            log.append("h2")

        bus.subscribe("MatchCreated", h1)
        bus.subscribe("MatchCreated", h2)
        bus.publish(MatchCreated())
        await asyncio.sleep(0)
        assert "h1" in log
        assert "h2" in log

    async def test_publish_without_subscribers_does_nothing(self) -> None:
        bus = EventBus()
        # 구독자 없을 때 예외 없이 통과
        bus.publish(MatchCreated())
        await asyncio.sleep(0)

    async def test_publish_only_triggers_matching_event_type(self) -> None:
        bus = EventBus()
        match_calls: list[DomainEvent] = []
        message_calls: list[DomainEvent] = []

        async def match_handler(event: DomainEvent) -> None:
            match_calls.append(event)

        async def message_handler(event: DomainEvent) -> None:
            message_calls.append(event)

        bus.subscribe("MatchCreated", match_handler)
        bus.subscribe("MessageCreated", message_handler)

        bus.publish(MatchCreated())
        await asyncio.sleep(0)

        assert len(match_calls) == 1
        assert len(message_calls) == 0

    async def test_publish_uses_class_name_as_event_type(self) -> None:
        """EventBus는 type(event).__name__ 을 이벤트 타입으로 사용한다."""
        bus = EventBus()
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe("MessageCreated", handler)
        bus.publish(MessageCreated(content="test"))
        await asyncio.sleep(0)
        assert len(received) == 1


class TestEventBusErrorIsolation:
    """핸들러 예외 격리 테스트 — 한 핸들러 실패가 다른 핸들러에 영향 없음."""

    async def test_failing_handler_does_not_prevent_other_handlers(self) -> None:
        bus = EventBus()
        second_called: list[bool] = []

        async def bad_handler(event: DomainEvent) -> None:
            raise RuntimeError("의도적인 오류")

        async def good_handler(event: DomainEvent) -> None:
            second_called.append(True)

        bus.subscribe("MatchCreated", bad_handler)
        bus.subscribe("MatchCreated", good_handler)
        bus.publish(MatchCreated())
        await asyncio.sleep(0)
        assert second_called == [True]

    async def test_failing_handler_does_not_raise_to_caller(self) -> None:
        bus = EventBus()

        async def bad_handler(event: DomainEvent) -> None:
            raise ValueError("핸들러 오류")

        bus.subscribe("MatchCreated", bad_handler)
        # publish 자체는 예외를 던지지 않아야 한다
        bus.publish(MatchCreated())
        await asyncio.sleep(0)  # task 실행 완료

    async def test_multiple_failing_handlers_all_isolated(self) -> None:
        bus = EventBus()
        log: list[str] = []

        async def fail1(event: DomainEvent) -> None:
            raise RuntimeError("fail1")

        async def fail2(event: DomainEvent) -> None:
            raise RuntimeError("fail2")

        async def ok(event: DomainEvent) -> None:
            log.append("ok")

        bus.subscribe("MatchCreated", fail1)
        bus.subscribe("MatchCreated", fail2)
        bus.subscribe("MatchCreated", ok)
        bus.publish(MatchCreated())
        await asyncio.sleep(0)
        assert log == ["ok"]


class TestEventBusStateIsolation:
    """EventBus 인스턴스 간 상태 격리 테스트."""

    async def test_two_buses_do_not_share_subscribers(self) -> None:
        bus1 = EventBus()
        bus2 = EventBus()
        calls: list[int] = []

        async def handler(event: DomainEvent) -> None:
            calls.append(1)

        bus1.subscribe("MatchCreated", handler)
        bus2.publish(MatchCreated())
        await asyncio.sleep(0)
        assert calls == []

    async def test_publish_after_unsubscribe_does_not_call_handler(self) -> None:
        bus = EventBus()
        calls: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            calls.append(event)

        bus.subscribe("MatchCreated", handler)
        bus.unsubscribe("MatchCreated", handler)
        bus.publish(MatchCreated())
        await asyncio.sleep(0)
        assert calls == []
