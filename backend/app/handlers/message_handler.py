from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from .. import db, deps
from ..auth.authorization_policy import check_match_participant
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth, get_event_bus, get_principal, reconstruct_agent_from_row
from ..pubsub.domain_events import MessageCreated

router = APIRouter(prefix="/v1/matches", tags=["messages"])


@router.get("/{match_id}/messages")
async def get_messages(
    match_id: UUID,
    limit: int = Query(50, le=100),
    cursor: UUID | None = Query(None),
    ctx=Depends(get_auth),
) -> dict:
    await check_match_participant(ctx, match_id)
    rows = await db.get_messages(match_id, limit=limit, before_id=cursor)
    items = [
        {k: str(v) if isinstance(v, UUID) else v for k, v in dict(r).items()}
        for r in reversed(rows)
    ]
    next_cursor = str(rows[-1]["message_id"]) if len(rows) == limit else None
    return envelope(data={"items": items, "next_cursor": next_cursor})


async def handle_send_message(
    match_id: UUID,
    sender_agent_id: UUID,
    content: str,
    principal,
    bus,
) -> dict:
    """WS send_message 액션. ws_transport.py 에서 호출한다."""
    match_row = await db.get_match(match_id)
    if match_row is None:
        raise KeyError(f"매치를 찾을 수 없습니다: {match_id}")

    agent_row = await db.get_agent_row(sender_agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {sender_agent_id}")
    if agent_row["principal_id"] != principal.principal_id:
        raise PermissionError("이 에이전트의 소유자가 아닙니다.")

    # 사용자 메시지 저장
    await db.insert_message(match_id, sender_agent_id, content)

    # 상대방 에이전트 ID 결정
    counterpart_agent_id = (
        match_row["agent_b_id"] if match_row["agent_a_id"] == sender_agent_id
        else match_row["agent_a_id"]
    )

    # 상대방 에이전트를 DB에서 로드해 personality 기반 응답 생성
    counterpart_row = await db.get_agent_full(counterpart_agent_id)
    if counterpart_row is None:
        raise KeyError(f"상대방 에이전트를 찾을 수 없습니다: {counterpart_agent_id}")
    counterpart_agent = reconstruct_agent_from_row(counterpart_row)

    response_text = counterpart_agent.sendMessage(match_id, content)
    resp_msg = await db.insert_message(match_id, counterpart_agent_id, response_text)

    bus.publish(MessageCreated(
        message_id=resp_msg["message_id"],
        match_id=match_id,
        sender_agent_id=counterpart_agent_id,
        content=response_text,
    ))

    return {"response": response_text, "message_id": str(resp_msg["message_id"])}
