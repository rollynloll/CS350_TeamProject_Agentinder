from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from models.date.date_session import DateOutcome, DateSession, DateStatus

from .. import db, deps
from ..auth.authorization_policy import check_agent_actor
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth, get_event_bus, get_principal
from ..pubsub.domain_events import DateEnded, DateStarted, MessageCreated
from ..services.matching_service_impl import MatchingServiceImpl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["auto-match"])


# ── 백그라운드 스케줄러 ────────────────────────────────────────────────────

async def run_background_loop(interval_seconds: int = 300) -> None:
    """auto_match=true 에이전트를 주기적으로 자율 매칭한다."""
    logger.info("auto-match background loop 시작 (주기 %ds)", interval_seconds)
    try:
        while True:
            await asyncio.sleep(interval_seconds)
            await _run_all_auto_match_agents()
    except asyncio.CancelledError:
        logger.info("auto-match background loop 종료")


async def _run_all_auto_match_agents() -> None:
    rows = await db.get_auto_match_agents()
    if not rows:
        return

    bus = deps.event_bus
    svc = MatchingServiceImpl(bus)

    logger.info("auto-match 루프 실행: 대상 에이전트 %d개", len(rows))
    for row in rows:
        try:
            session = await svc.runAsyncMatch(row["agent_id"])
            if session is not None:
                await _launch_date_session(session, bus)
        except Exception:
            logger.exception("auto-match: agent=%s 처리 중 오류", row["agent_id"])


async def _launch_date_session(session: DateSession, bus) -> None:
    """DB date 레코드를 생성하고 DateSession을 백그라운드로 실행한다."""
    await db.insert_date_with_id(session.date_id, session.match_id, "coffee_chat")
    await db.start_date(session.date_id)
    asyncio.create_task(_run_and_persist(session, bus))


# ── DateSession 실행 및 결과 영속화 ──────────────────────────────────────

async def _run_and_persist(session: DateSession, bus) -> None:
    """DateSession.run() 완료 후 transcript·rating·관계를 DB에 저장한다."""
    agent_a_id: UUID = session._agent_a.agent_id
    agent_b_id: UUID = session._agent_b.agent_id

    try:
        bus.publish(DateStarted(date_id=session.date_id, match_id=session.match_id))
        result = await session.run()

        # ── 1. 대화 내용 저장 ──────────────────────────────────────────
        # transcript role: "assistant" → agent_a, "user" → agent_b
        for msg in result.transcript:
            sender_id = agent_a_id if msg.role == "assistant" else agent_b_id
            msg_row = await db.insert_message(session.match_id, sender_id, msg.content)
            bus.publish(MessageCreated(
                message_id=msg_row["message_id"],
                match_id=session.match_id,
                sender_agent_id=sender_id,
                content=msg.content,
            ))

        # ── 2. 데이트 종료 ─────────────────────────────────────────────
        is_noshow = result.status == DateStatus.NO_SHOW
        await db.end_date(session.date_id, result.outcome.value, is_noshow)

        # ── 3. 평점 저장 ───────────────────────────────────────────────
        for rating in result.ratings:
            await db.insert_rating(
                date_id=rating.date_id,
                rater_principal_id=rating.rater_principal_id,
                rated_agent_id=rating.rated_agent_id,
                stars=rating.stars,
                compatibility=rating.compatibility,
            )

        # ── 4. 신뢰 점수 + 관계 티어 갱신 ─────────────────────────────
        sm = deps.score_manager
        if sm is not None:
            for aid in (agent_a_id, agent_b_id):
                trust = sm.getTrust(aid)
                breakdown = sm.getTrustBreakdown(aid)
                if breakdown is not None:
                    await db.upsert_trust_score(
                        agent_id=aid,
                        composite=trust,
                        peer_ratings_avg=breakdown.peer_ratings_avg,
                        data_point_count=breakdown.data_point_count,
                    )

            if result.outcome == DateOutcome.SUCCESSFUL and result.ratings:
                avg_stars = sum(r.stars for r in result.ratings) / len(result.ratings)
                sm.recordSuccessfulDate(agent_a_id, agent_b_id, avg_stars / 5.0)

            rel = sm._get_or_create_rel(agent_a_id, agent_b_id)
            new_tier = sm.checkUpgrade(agent_a_id, agent_b_id)
            await db.upsert_relationship(
                agent_a_id=agent_a_id,
                agent_b_id=agent_b_id,
                successful_dates=rel.successful_dates,
                avg_rating=rel.avg_rating or 0.0,
                tier=(new_tier or rel.tier).value,
            )
            if new_tier is not None:
                await db.update_agent_tier(agent_a_id, new_tier.value)
                await db.update_agent_tier(agent_b_id, new_tier.value)

        bus.publish(DateEnded(
            date_id=session.date_id,
            match_id=session.match_id,
            outcome=result.outcome.value,
        ))
        logger.info(
            "date 완료: date=%s outcome=%s trust_delta=%.4f imbalanced=%s",
            session.date_id, result.outcome.value, result.trust_delta, result.is_imbalanced,
        )

    except Exception:
        logger.exception("date 실패: date=%s", session.date_id)
        try:
            await db.end_date(session.date_id, "failed")
        except Exception:
            pass


# ── API 엔드포인트 ────────────────────────────────────────────────────────

class AiMatchRequest(BaseModel):
    topic: str


@router.post("/{agent_id}/ai-match")
async def run_ai_match(
    agent_id: UUID,
    body: AiMatchRequest,
    principal=Depends(get_principal),
    bus=Depends(get_event_bus),
    ctx=Depends(get_auth),
) -> dict:
    """AI 호환성 기반 매칭 + 즉시 데이트 시작.

    - compat 최고점 상대를 선택한다.
    - skipTrustCheck=False (동기 매칭)
    """
    agent_row = await db.get_agent_row(agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    check_agent_actor(ctx, agent_id, agent_row)

    svc = MatchingServiceImpl(bus)
    session = await svc.runAiMatch(agent_id, body.topic)

    if session is None:
        return envelope(data={"matched": False, "reason": "no_suitable_partner"})

    await _launch_date_session(session, bus)
    return envelope(data={
        "matched": True,
        "match_id": str(session.match_id),
        "date_id": str(session.date_id),
    })


@router.post("/{agent_id}/auto-match/run")
async def run_auto_match_for_agent(
    agent_id: UUID,
    principal=Depends(get_principal),
    bus=Depends(get_event_bus),
    ctx=Depends(get_auth),
) -> dict:
    """특정 에이전트의 자율 매칭을 즉시 실행한다."""
    agent_row = await db.get_agent_row(agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    check_agent_actor(ctx, agent_id, agent_row)

    svc = MatchingServiceImpl(bus)
    session = await svc.runAsyncMatch(agent_id)

    if session is None:
        return envelope(data={"matched": False, "reason": "no_eligible_partner"})

    await _launch_date_session(session, bus)
    return envelope(data={
        "matched": True,
        "match_id": str(session.match_id),
        "date_id": str(session.date_id),
    })


@router.post("/auto-match/run")
async def run_auto_match_all(
    principal=Depends(get_principal),
    bus=Depends(get_event_bus),
) -> dict:
    """현재 Principal이 소유한 auto_match=true 에이전트 전체에 대해 자율 매칭을 실행한다."""
    agent_list = await db.get_principal_agents(principal.principal_id)
    svc = MatchingServiceImpl(bus)

    results = []
    for row in agent_list:
        full = await db.get_agent_row(row["agent_id"])
        if full is None or not full.get("auto_match"):
            continue
        session = await svc.runAsyncMatch(row["agent_id"])
        if session is not None:
            await _launch_date_session(session, bus)
            results.append({
                "agent_id": str(row["agent_id"]),
                "matched": True,
                "match_id": str(session.match_id),
            })
        else:
            results.append({"agent_id": str(row["agent_id"]), "matched": False})

    return envelope(data={"results": results, "total_agents": len(results)})
