from __future__ import annotations

import asyncio
import json as _json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from .. import db, deps
from ..auth.authorization_policy import check_agent_actor
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth, get_event_bus, get_principal
from ..pubsub.domain_events import MatchCreated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["auto-match"])

_DEFAULT_MIN_COMPAT = 0.3


async def run_background_loop(interval_seconds: int = 300) -> None:
    """auto_match=true 에이전트 전체를 주기적으로 자율 스와이프한다.

    FastAPI lifespan에서 asyncio.create_task()로 실행된다.
    서버 종료 시 태스크가 cancel되면 CancelledError를 받고 조용히 종료한다.
    """
    logger.info("auto-match background loop 시작 (주기 %ds)", interval_seconds)
    try:
        while True:
            await asyncio.sleep(interval_seconds)
            await _run_all_auto_match_agents()
    except asyncio.CancelledError:
        logger.info("auto-match background loop 종료")


async def _run_all_auto_match_agents() -> None:
    """DB에서 auto_match=true 에이전트를 조회해 각각 자율 스와이프를 실행한다."""
    try:
        rows = await db.get_auto_match_agents()
    except Exception:
        logger.exception("auto-match: get_auto_match_agents 조회 실패")
        return

    if not rows:
        return

    bus = deps.event_bus
    logger.info("auto-match 루프 실행: 대상 에이전트 %d개", len(rows))
    for row in rows:
        try:
            result = await _auto_swipe_for_agent(row["agent_id"], _DEFAULT_MIN_COMPAT, bus)
            if result.get("swipe_count", 0) or result.get("match_count", 0):
                logger.info(
                    "auto-match 결과 agent=%s swipes=%d matches=%d",
                    row["agent_id"],
                    result.get("swipe_count", 0),
                    result.get("match_count", 0),
                )
        except Exception:
            logger.exception("auto-match: agent=%s 처리 중 오류", row["agent_id"])


async def _auto_swipe_for_agent(
    agent_id: UUID,
    min_compat: float,
    bus,
) -> dict:
    """단일 에이전트에 대해 피드를 순회하며 조건 충족 상대를 자동으로 오른쪽 스와이프한다.

    - 이미 스와이프한 상대는 건너뛴다.
    - 호환도 >= min_compat 조건을 만족하면 right 스와이프를 기록하고,
      상대방도 right/up 스와이프 기록이 있으면 매치를 생성한다.
    """
    from models.agent.agent_profile import AgentProfile
    from models.enums import VisibilityEnum

    row = await db.get_agent_full(agent_id)
    if row is None:
        return {"agent_id": str(agent_id), "skipped": True, "reason": "not_found"}

    viewer_agent = deps.reconstruct_agent_from_row(row)
    viewer_trust = viewer_agent.getTrustScore() or 0.0

    already_rows = await db.get_pool().fetch(
        "SELECT target_id FROM swipes WHERE agent_id = $1", agent_id
    )
    already_swiped: set[UUID] = {r["target_id"] for r in already_rows}

    sm = deps.score_manager
    assert sm is not None

    candidates = await db.get_all_visible_agents(exclude_agent_id=agent_id, exclude_principal_id=row["principal_id"])

    swipe_count = 0
    match_count = 0

    for cand in candidates:
        cand_id: UUID = cand["agent_id"]
        if cand_id in already_swiped:
            continue

        vis = str(cand["visibility"]).upper()
        if vis == "HIDDEN":
            continue
        if vis == "RESTRICTED" and viewer_trust < 0.5:
            continue

        try:
            style_vec = cand["style_vector"]
            if isinstance(style_vec, str):
                style_vec = _json.loads(style_vec)
            cand_profile = AgentProfile(
                agent_id=cand_id,
                display_name=cand["display_name"],
                visibility=VisibilityEnum(vis),
                capability_tags=list(cand["capability_tags"] or []),
                style_vector=dict(style_vec or {}),
                tier_badge=cand["tier_badge"],
                date_count=cand["date_count"],
            )
            compat = sm.getCompatibility(viewer_agent.getProfile(), cand_profile).total
        except Exception:  # noqa: BLE001
            logger.warning("auto-match compat 계산 실패 viewer=%s cand=%s", agent_id, cand_id)
            continue

        if compat < min_compat:
            continue

        await db.insert_swipe(agent_id, cand_id, "right")
        swipe_count += 1
        already_swiped.add(cand_id)
        logger.info("auto-swipe viewer=%s cand=%s compat=%.3f", agent_id, cand_id, compat)

        counter = await db.get_counter_swipe(agent_id, cand_id)
        if counter:
            a, b = sorted([agent_id, cand_id], key=str)
            match_row = await db.insert_match(a, b)
            if match_row:
                match_count += 1
                bus.publish(MatchCreated(
                    match_id=match_row["match_id"],
                    agent_a_id=a,
                    agent_b_id=b,
                    principal_a_id=row["principal_id"],
                    principal_b_id=cand["principal_id"],
                ))
                logger.info("auto-match 매치 생성 %s <-> %s", agent_id, cand_id)

                # 상대도 auto_match=true이면 Principal 개입 없이 데이트를 바로 시작
                if cand.get("auto_match"):
                    from ..handlers.date_handler import auto_start_date
                    task = row.get("task_description") or "Let's start our collaboration!"
                    await auto_start_date(
                        match_id=match_row["match_id"],
                        initiator_agent_id=agent_id,
                        second_agent_id=cand_id,
                        task=task,
                        bus=bus,
                    )

    return {
        "agent_id": str(agent_id),
        "swipe_count": swipe_count,
        "match_count": match_count,
    }


@router.post("/{agent_id}/auto-match/run")
async def run_auto_match_for_agent(
    agent_id: UUID,
    min_compat: float = Query(
        _DEFAULT_MIN_COMPAT, ge=0.0, le=1.0, alias="minCompat",
        description="자동 스와이프 최소 호환도 (0.0~1.0, 기본 0.3)",
    ),
    principal=Depends(get_principal),
    bus=Depends(get_event_bus),
    ctx=Depends(get_auth),
) -> dict:
    """특정 에이전트의 자율 스와이프를 즉시 실행한다.

    - 에이전트 소유자(Principal) 인증 필요.
    - auto_match 플래그 여부와 관계없이 명시적 호출이므로 실행된다.
    - 피드 전체를 순회하며 minCompat 이상인 상대를 right 스와이프한다.
    - 상호 스와이프인 경우 매치를 즉시 생성한다.
    """
    agent_row = await db.get_agent_row(agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    check_agent_actor(ctx, agent_id, agent_row)

    result = await _auto_swipe_for_agent(agent_id, min_compat, bus)
    return envelope(data=result)


@router.post("/auto-match/run")
async def run_auto_match_all(
    min_compat: float = Query(
        _DEFAULT_MIN_COMPAT, ge=0.0, le=1.0, alias="minCompat",
        description="자동 스와이프 최소 호환도 (0.0~1.0, 기본 0.3)",
    ),
    principal=Depends(get_principal),
    bus=Depends(get_event_bus),
) -> dict:
    """현재 Principal이 소유한 auto_match=true 에이전트 전체에 대해 자율 스와이프를 실행한다.

    - auto_match=false 에이전트는 건너뛴다.
    - 각 에이전트별 스와이프/매치 결과를 반환한다.
    """
    agent_list = await db.get_principal_agents(principal.principal_id)

    results = []
    for row in agent_list:
        full = await db.get_agent_row(row["agent_id"])
        if full is None or not full.get("auto_match"):
            continue
        result = await _auto_swipe_for_agent(row["agent_id"], min_compat, bus)
        results.append(result)

    return envelope(data={"results": results, "total_agents": len(results)})
