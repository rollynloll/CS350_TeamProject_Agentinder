from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from .. import db
from ..auth.error_handler_middleware import envelope
from ..deps import agent_service, get_event_bus, get_principal, score_manager
from ..pubsub.domain_events import MatchCreated

router = APIRouter(prefix="/v1/agents", tags=["feed"])


@router.get("/{agent_id}/feed")
async def get_feed(
    agent_id: UUID,
    cursor: UUID | None = Query(None),
    limit: int = Query(20, le=50),
    principal=Depends(get_principal),
) -> dict:
    from models.enums import VisibilityEnum

    agent_row = await db.get_agent_row(agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    if agent_row["principal_id"] != principal.principal_id:
        raise PermissionError("이 에이전트의 소유자가 아닙니다.")

    viewer_agent = next((a for a in principal.agents if a.agent_id == agent_id), None)
    if viewer_agent is None and agent_service is not None:
        try:
            viewer_agent = agent_service.get(agent_id)
        except KeyError:
            pass
    if viewer_agent is None:
        raise KeyError(f"에이전트 인스턴스를 찾을 수 없습니다: {agent_id}")

    viewer_trust = viewer_agent.getTrustScore() or 0.0
    already_swiped = {
        r["target_id"]
        for r in await db.get_pool().fetch(
            "SELECT target_id FROM swipes WHERE agent_id = $1", agent_id
        )
    }

    candidates = await db.get_all_visible_agents(exclude_agent_id=agent_id)
    results = []

    sm = score_manager
    assert sm is not None

    for row in candidates:
        cand_id = row["agent_id"]
        if cand_id in already_swiped:
            continue

        vis = str(row["visibility"]).upper()
        if vis == VisibilityEnum.HIDDEN.value:
            continue
        if vis == VisibilityEnum.RESTRICTED.value and viewer_trust < 0.5:
            continue

        # 호환성 점수 계산 (capability_embedding None 이면 fallback)
        try:
            cand_agent = agent_service.get(cand_id) if agent_service else None
            if cand_agent is not None:
                score = sm.getCompatibility(viewer_agent.getProfile(), cand_agent.getProfile())
                compat_total = round(score.total, 3)
                common_tags = score.common_tags
            else:
                compat_total, common_tags = 0.5, []
        except Exception:
            compat_total, common_tags = 0.5, []

        results.append({
            "agent_id": str(cand_id),
            "display_name": row["display_name"],
            "avatar_url": row["avatar_url"],
            "tier_badge": row["tier_badge"],
            "trust_score": row["trust_score"],
            "compatibility_total": compat_total,
            "common_tags": common_tags,
        })

    results.sort(key=lambda x: x["compatibility_total"], reverse=True)

    if cursor:
        start = next((i for i, r in enumerate(results) if r["agent_id"] == str(cursor)), 0)
        results = results[start:]

    page = results[:limit]
    next_cursor = page[-1]["agent_id"] if len(page) == limit else None
    return envelope(data={"items": page, "next_cursor": next_cursor})


class SwipeRequest(BaseModel):
    target_id: UUID
    direction: str  # right | left | up


@router.post("/{agent_id}/swipe")
async def swipe(
    agent_id: UUID,
    body: SwipeRequest,
    principal=Depends(get_principal),
    bus=Depends(get_event_bus),
) -> dict:
    agent_row = await db.get_agent_row(agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    if agent_row["principal_id"] != principal.principal_id:
        raise PermissionError("이 에이전트의 소유자가 아닙니다.")

    direction = body.direction.lower()
    if direction not in ("right", "left", "up"):
        raise ValueError(f"유효하지 않은 direction: {direction}")

    await db.insert_swipe(agent_id, body.target_id, direction)

    match_row = None
    if direction in ("right", "up"):
        counter = await db.get_counter_swipe(agent_id, body.target_id)
        if counter:
            a, b = sorted([agent_id, body.target_id], key=str)
            match_row = await db.insert_match(a, b)
            if match_row:
                target_row = await db.get_agent_row(body.target_id)
                bus.publish(MatchCreated(
                    match_id=match_row["match_id"],
                    agent_a_id=a,
                    agent_b_id=b,
                    principal_a_id=agent_row["principal_id"],
                    principal_b_id=target_row["principal_id"] if target_row else None,
                ))

    return envelope(data={
        "swiped": True,
        "match": {"match_id": str(match_row["match_id"])} if match_row else None,
    })
