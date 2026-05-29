from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import db
from ..auth.authorization_policy import check_date_participant, check_match_participant
from ..auth.error_handler_middleware import envelope
from ..deps import agent_service, get_auth, get_event_bus, get_principal, score_manager
from ..pubsub.domain_events import DateEnded, DateProposed, DateStarted

router = APIRouter(tags=["dates"])

# WS join_date 대기: date_id → 첫 번째 참여자 agent_id (결정 #2)
_pending_joins: dict[UUID, UUID] = {}


class ProposeDateRequest(BaseModel):
    type: str | None = None
    scheduled_at: datetime | None = None


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

    agent_a = await db.get_agent_row(match_row["agent_a_id"])
    agent_b = await db.get_agent_row(match_row["agent_b_id"])
    target_principal_id = None
    for row in (agent_a, agent_b):
        if row and row["principal_id"] != ctx.principal_id:
            target_principal_id = row["principal_id"]
            break

    date_row = await db.insert_date(match_id, body.type, body.scheduled_at)
    bus.publish(DateProposed(
        date_id=date_row["date_id"],
        match_id=match_id,
        proposer_principal_id=ctx.principal_id,
        target_principal_id=target_principal_id,
    ))
    return envelope(data={k: str(v) if isinstance(v, UUID) else v for k, v in dict(date_row).items()})


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
    if agent is None and agent_service is not None:
        try:
            agent = agent_service.get(agent_id)
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
        if agent is None and agent_service is not None:
            try:
                agent = agent_service.get(aid)
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
            compatibility=int((body.rating_compatibility or 0.8) * 5),
            comments="",
            issues=[],
        )
        principal.submitRating(date_id, rating)

        sm = score_manager
        assert sm is not None
        sm.recordSuccessfulDate(
            match_row["agent_a_id"],
            match_row["agent_b_id"],
            body.rating_stars / 5.0,
        )
        sm.checkUpgrade(match_row["agent_a_id"], match_row["agent_b_id"])

    bus.publish(DateEnded(date_id=date_id, match_id=date_row["match_id"], outcome=body.outcome))
    return envelope(data={"date_id": str(date_id), "outcome": body.outcome})
