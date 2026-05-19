from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from .domain_events import DomainEvent

logger = logging.getLogger(__name__)

Handler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventBus:
    """V1: asyncio 인메모리 이벤트 버스. 핸들러 예외는 격리해 로깅만 한다."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type] = [
            h for h in self._subscribers[event_type] if h is not handler
        ]

    def publish(self, event: DomainEvent) -> None:
        event_type = type(event).__name__
        for handler in self._subscribers.get(event_type, []):
            asyncio.create_task(self._safe_call(handler, event))

    @staticmethod
    async def _safe_call(handler: Handler, event: DomainEvent) -> None:
        try:
            await handler(event)
        except Exception:
            logger.exception("EventBus handler error for %s", type(event).__name__)
