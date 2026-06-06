from __future__ import annotations

import json
import logging
from collections import defaultdict
from uuid import UUID

import httpx
from fastapi import WebSocket
from jose import JWTError

from ..auth.auth_middleware import AuthMiddleware
from ..pubsub.domain_events import (
    DateEnded,
    DateProposed,
    DateStarted,
    DomainEvent,
    MatchCreated,
    MessageCreated,
)

logger = logging.getLogger(__name__)


class WSGateway:
    """WebSocket 연결 레지스트리 + 토픽 구독 + 이벤트 push."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._topics: dict[str, set[WebSocket]] = defaultdict(set)

    async def on_connect(self, ws: WebSocket, token: str) -> UUID | None:
        # REST AuthMiddleware와 동일한 alg-aware 검증을 사용한다.
        # Supabase는 ES256(JWKS), dev JWT는 HS256(shared secret)으로 발급되므로
        # 한쪽만 지원하면 다른 한쪽 토큰을 들고 온 클라이언트가 4001로 끊긴다.
        try:
            ctx = await AuthMiddleware._verify(token)
            principal_id = ctx.principal_id
        except (JWTError, ValueError, KeyError, httpx.HTTPError) as exc:
            logger.warning("WS 인증 실패 (%s): %s", type(exc).__name__, exc)
            await ws.close(code=4001)
            return None
        except Exception:
            logger.error("WS 인증 중 예상치 못한 오류", exc_info=True)
            await ws.close(code=4001)
            return None

        await ws.accept()
        self._connections[principal_id].add(ws)
        logger.debug("WS 연결: principal=%s", principal_id)
        return principal_id

    async def on_disconnect(self, ws: WebSocket, principal_id: UUID) -> None:
        self._connections[principal_id].discard(ws)
        for subs in self._topics.values():
            subs.discard(ws)

    def subscribe_topic(self, ws: WebSocket, topic: str) -> None:
        self._topics[topic].add(ws)

    def unsubscribe_topic(self, ws: WebSocket, topic: str) -> None:
        self._topics[topic].discard(ws)

    async def push_to_topic(self, topic: str, event: dict) -> None:
        payload = json.dumps(event)
        dead: list[WebSocket] = []
        for ws in list(self._topics.get(topic, [])):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._topics[topic].discard(ws)

    # ── EventBus 구독자 ───────────────────────────────────────────────────

    async def on_domain_event(self, event: DomainEvent) -> None:
        if isinstance(event, MatchCreated):
            payload = {"event": "new_match", "match_id": str(event.match_id)}
            if event.principal_a_id:
                await self.push_to_topic(f"matches.{event.principal_a_id}", payload)
            if event.principal_b_id:
                await self.push_to_topic(f"matches.{event.principal_b_id}", payload)

        elif isinstance(event, DateProposed):
            payload = {"event": "date_proposed", "date_id": str(event.date_id)}
            if event.target_principal_id:
                await self.push_to_topic(f"notifications.{event.target_principal_id}", payload)

        elif isinstance(event, DateStarted):
            await self.push_to_topic(
                f"date.{event.date_id}",
                {"event": "date_started", "date_id": str(event.date_id)},
            )

        elif isinstance(event, DateEnded):
            await self.push_to_topic(
                f"date.{event.date_id}",
                {"event": "date_ended", "date_id": str(event.date_id), "outcome": event.outcome},
            )

        elif isinstance(event, MessageCreated):
            await self.push_to_topic(
                f"chat.{event.match_id}",
                {
                    "event": "message",
                    "message_id": str(event.message_id),
                    "match_id": str(event.match_id),
                    "sender_agent_id": str(event.sender_agent_id),
                    "content": event.content,
                },
            )
