from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..deps import _principal_cache, get_event_bus, get_ws_gateway
from ..handlers import date_handler, message_handler

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/v1/ws")
async def websocket_endpoint(ws: WebSocket, token: str) -> None:
    gw = get_ws_gateway()
    principal_id = await gw.on_connect(ws, token)
    if principal_id is None:
        return

    try:
        while True:
            raw = await ws.receive_text()
            try:
                frame = json.loads(raw)
                await _dispatch(ws, frame, principal_id)
            except Exception as exc:
                logger.warning("WS frame error: %s", exc)
                await ws.send_text(json.dumps({"error": str(exc)}))
    except WebSocketDisconnect:
        pass
    finally:
        await gw.on_disconnect(ws, principal_id)


async def _dispatch(ws: WebSocket, frame: dict, principal_id: UUID) -> None:
    topic: str = frame.get("topic", "")
    event: str = frame.get("event", "")
    payload: dict = frame.get("payload", {})

    gw = get_ws_gateway()
    bus = get_event_bus()

    if event == "subscribe":
        gw.subscribe_topic(ws, topic)
        await ws.send_text(json.dumps({"event": "subscribed", "topic": topic}))
        return

    if event == "unsubscribe":
        gw.unsubscribe_topic(ws, topic)
        await ws.send_text(json.dumps({"event": "unsubscribed", "topic": topic}))
        return

    principal = _principal_cache.get(principal_id)
    if principal is None:
        await ws.send_text(json.dumps({"error": "Principal 세션 없음. REST 로그인 후 사용하세요."}))
        return

    if event == "send_message":
        result = await message_handler.handle_send_message(
            match_id=UUID(payload["match_id"]),
            sender_agent_id=UUID(payload["agent_id"]),
            content=payload["content"],
            principal=principal,
            bus=bus,
        )
        await ws.send_text(json.dumps({"event": "message_sent", **result}))

    elif event == "join_date":
        result = await date_handler.handle_join_date(
            date_id=UUID(payload["date_id"]),
            agent_id=UUID(payload["agent_id"]),
            principal=principal,
            bus=bus,
        )
        await ws.send_text(json.dumps({"event": "date_joined", **result}))

    else:
        await ws.send_text(json.dumps({"error": f"알 수 없는 이벤트: {event}"}))
