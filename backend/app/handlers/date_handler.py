from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MAX_MESSAGES = 20  # REQ-0301: Coffee Chat 최대 메시지 수

from .. import db, deps
from ..auth.authorization_policy import check_date_participant, check_match_participant
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth, get_event_bus, get_principal, reconstruct_agent_from_row
from ..pubsub.domain_events import DateEnded, DateProposed, DateStarted, MessageCreated

router = APIRouter(tags=["dates"])

# WS join_date 대기: date_id → 첫 번째 참여자 agent_id (결정 #2)
_pending_joins: dict[UUID, UUID] = {}

# Option B: 양쪽이 모두 propose_date를 눌러야 대화 시작
# match_id → {date_id, initiator_agent_id, first_message}
_pending_starts: dict[UUID, dict] = {}


class ProposeDateRequest(BaseModel):
    type: str | None = None
    scheduled_at: datetime | None = None
    message: str | None = None  # 에이전트 대화 시작 태스크 컨텍스트


@router.post("/v1/matches/{match_id}/dates")
async def propose_date(
    match_id: UUID,
    body: ProposeDateRequest,
    principal=Depends(get_principal),
    ctx=Depends(get_auth),
    bus=Depends(get_event_bus),
) -> dict:
    await check_match_participant(ctx, match_id)

    match_row = await db.get_match(match_id)
    if match_row is None:
        raise KeyError(f"매치를 찾을 수 없습니다: {match_id}")

    # 이 매치에서 호출자 소유 에이전트와 상대 에이전트 구분
    my_agent_ids = {a.agent_id for a in principal.agents}
    caller_agent_id = next(
        (aid for aid in (match_row["agent_a_id"], match_row["agent_b_id"]) if aid in my_agent_ids),
        None,
    )
    if caller_agent_id is None:
        raise PermissionError("이 매치의 참여 에이전트를 찾을 수 없습니다.")
    counterpart_agent_id = (
        match_row["agent_b_id"] if caller_agent_id == match_row["agent_a_id"]
        else match_row["agent_a_id"]
    )

    task = body.message or f"Let's start our {body.type or 'date'}!"

    if match_id not in _pending_starts:
        # 첫 번째 호출자: date 레코드 생성, 첫 메시지 생성 후 대기
        date_row = await db.insert_date(match_id, body.type, body.scheduled_at)
        date_id = date_row["date_id"]

        caller_row = await db.get_agent_full(caller_agent_id)
        if caller_row is None:
            raise KeyError(f"에이전트를 찾을 수 없습니다: {caller_agent_id}")
        caller_agent = reconstruct_agent_from_row(caller_row)
        first_message = caller_agent.sendMessage(match_id, task)

        _pending_starts[match_id] = {
            "date_id": date_id,
            "initiator_agent_id": caller_agent_id,
            "first_message": first_message,
        }

        bus.publish(DateProposed(
            date_id=date_id,
            match_id=match_id,
            proposer_principal_id=ctx.principal_id,
            target_principal_id=None,
        ))
        return envelope(data={
            "date_id": str(date_id),
            "match_id": str(match_id),
            "waiting": True,
            "started": False,
        })

    else:
        # 두 번째 호출자: 양쪽 준비 완료 → 대화 루프 백그라운드 시작
        pending = _pending_starts.pop(match_id)
        date_id = pending["date_id"]
        initiator_agent_id = pending["initiator_agent_id"]
        first_message = pending["first_message"]

        await db.start_date(date_id)
        bus.publish(DateStarted(date_id=date_id, match_id=match_id))

        # HTTP 응답을 블록하지 않도록 대화 루프를 백그라운드 태스크로 실행
        asyncio.create_task(
            _run_conversation_loop(
                match_id=match_id,
                date_id=date_id,
                initiator_agent_id=initiator_agent_id,
                first_message=first_message,
                second_agent_id=caller_agent_id,
                bus=bus,
            )
        )

        return envelope(data={
            "date_id": str(date_id),
            "match_id": str(match_id),
            "waiting": False,
            "started": True,
        })


async def _run_conversation_loop(
    match_id: UUID,
    date_id: UUID,
    initiator_agent_id: UUID,
    first_message: str,
    second_agent_id: UUID,
    bus,
) -> None:
    """두 에이전트가 MAX_MESSAGES 또는 date 종료까지 번갈아 대화한다."""
    try:
        initiator_row = await db.get_agent_full(initiator_agent_id)
        second_row = await db.get_agent_full(second_agent_id)
        if initiator_row is None or second_row is None:
            return

        initiator = reconstruct_agent_from_row(initiator_row)
        second = reconstruct_agent_from_row(second_row)

        # 순서: [initiator, second, initiator, second, ...]
        # 첫 메시지(initiator)는 이미 생성됐으므로 second 응답부터 시작
        agents = [
            (second_agent_id, second),
            (initiator_agent_id, initiator),
        ]
        last_message = first_message
        msg_count = 1  # 첫 메시지(initiator) 포함

        # 첫 메시지 저장 + push
        first_row = await db.insert_message(match_id, initiator_agent_id, first_message)
        bus.publish(MessageCreated(
            message_id=first_row["message_id"],
            match_id=match_id,
            sender_agent_id=initiator_agent_id,
            content=first_message,
        ))

        while msg_count < MAX_MESSAGES:
            # date가 이미 종료됐는지 확인
            date_row = await db.get_date(date_id)
            if date_row is None or date_row["ended_at"] is not None:
                break

            sender_id, sender_agent = agents[msg_count % 2]
            reply = sender_agent.sendMessage(match_id, last_message)
            row = await db.insert_message(match_id, sender_id, reply)
            bus.publish(MessageCreated(
                message_id=row["message_id"],
                match_id=match_id,
                sender_agent_id=sender_id,
                content=reply,
            ))
            last_message = reply
            msg_count += 1

        # 메시지 한도 도달 시 date 자동 종료
        if msg_count >= MAX_MESSAGES:
            await db.end_date(date_id, outcome="completed")
            bus.publish(DateEnded(date_id=date_id, match_id=match_id, outcome="completed"))
            logger.info("date %s: MAX_MESSAGES(%d) 도달, 자동 종료", date_id, MAX_MESSAGES)

    except Exception:
        logger.exception("대화 루프 오류 (date_id=%s)", date_id)



@router.get("/v1/dates/{date_id}")
async def get_date(date_id: UUID, ctx=Depends(get_auth)) -> dict:
    await check_date_participant(ctx, date_id)
    row = await db.get_date(date_id)
    if row is None:
        raise KeyError(f"데이트를 찾을 수 없습니다: {date_id}")
    return envelope(data={k: str(v) if isinstance(v, UUID) else v for k, v in dict(row).items()})


async def handle_join_date(date_id: UUID, agent_id: UUID, principal, bus) -> dict:
    """WS join_date 액션 처리 (결정 #2: 상대 join 시 DateStarted)."""
    date_row = await db.get_date(date_id)
    if date_row is None:
        raise KeyError(f"데이트를 찾을 수 없습니다: {date_id}")

    agent = next((a for a in principal.agents if a.agent_id == agent_id), None)
    if agent is None and deps.agent_service is not None:
        try:
            agent = deps.agent_service.get(agent_id)
        except KeyError:
            pass
    if agent is None:
        raise KeyError(f"에이전트 인스턴스 없음: {agent_id}")

    agent.joinDate(date_id)

    if date_id not in _pending_joins:
        _pending_joins[date_id] = agent_id
        return {"joined": True, "started": False}

    del _pending_joins[date_id]
    await db.start_date(date_id)
    bus.publish(DateStarted(date_id=date_id, match_id=date_row["match_id"]))
    return {"joined": True, "started": True}


class EndDateRequest(BaseModel):
    outcome: str | None = None
    rating_stars: int | None = None
    rating_compatibility: float | None = None
    rated_agent_id: UUID | None = None


@router.post("/v1/dates/{date_id}/end")
async def end_date(
    date_id: UUID,
    body: EndDateRequest,
    principal=Depends(get_principal),
    ctx=Depends(get_auth),
    bus=Depends(get_event_bus),
) -> dict:
    await check_date_participant(ctx, date_id)

    date_row = await db.get_date(date_id)
    if date_row is None:
        raise KeyError(f"데이트를 찾을 수 없습니다: {date_id}")

    match_row = await db.get_match(date_row["match_id"])
    if match_row is None:
        raise KeyError("매치를 찾을 수 없습니다.")

    for aid in (match_row["agent_a_id"], match_row["agent_b_id"]):
        agent = next((a for a in principal.agents if a.agent_id == aid), None)
        if agent is None and deps.agent_service is not None:
            try:
                agent = deps.agent_service.get(aid)
            except KeyError:
                pass
        if agent:
            agent.leaveDate(date_id)

    await db.end_date(date_id, body.outcome)

    if body.rated_agent_id and body.rating_stars:
        from models import Rating
        rating = Rating(
            date_id=date_id,
            rater_principal_id=principal.principal_id,
            rated_agent_id=body.rated_agent_id,
            stars=body.rating_stars,
            compatibility=body.rating_compatibility or 0.8,
            comments="",
            issues=[],
        )
        principal.submitRating(date_id, rating)

        sm = deps.score_manager
        assert sm is not None
        sm.recordSuccessfulDate(
            match_row["agent_a_id"],
            match_row["agent_b_id"],
            body.rating_stars / 5.0,
        )
        sm.checkUpgrade(match_row["agent_a_id"], match_row["agent_b_id"])

    # 평점 및 관계 DB 영속화
    if body.rated_agent_id and body.rating_stars:
        compat_val = body.rating_compatibility or 0.8
        await db.insert_rating(
            date_id=date_id,
            rater_principal_id=principal.principal_id,
            rated_agent_id=body.rated_agent_id,
            stars=body.rating_stars,
            compatibility=compat_val,
        )

        sm = deps.score_manager
        if sm is not None:
            rel = sm._get_or_create_rel(match_row["agent_a_id"], match_row["agent_b_id"])
            new_tier = sm.checkUpgrade(match_row["agent_a_id"], match_row["agent_b_id"])
            await db.upsert_relationship(
                agent_a_id=match_row["agent_a_id"],
                agent_b_id=match_row["agent_b_id"],
                successful_dates=rel.successful_dates,
                avg_rating=rel.avg_rating or 0.0,
                tier=(new_tier or rel.tier).value,
            )
            if new_tier is not None:
                await db.update_agent_tier(match_row["agent_a_id"], new_tier.value)
                await db.update_agent_tier(match_row["agent_b_id"], new_tier.value)

            trust = sm.getTrust(body.rated_agent_id)
            breakdown = sm.getTrustBreakdown(body.rated_agent_id)
            if breakdown is not None:
                await db.upsert_trust_score(
                    agent_id=body.rated_agent_id,
                    composite=trust,
                    peer_ratings_avg=breakdown.peer_ratings_avg,
                    data_point_count=breakdown.data_point_count,
                )

    bus.publish(DateEnded(date_id=date_id, match_id=date_row["match_id"], outcome=body.outcome))
    return envelope(data={"date_id": str(date_id), "outcome": body.outcome})
