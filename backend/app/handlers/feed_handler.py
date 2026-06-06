from __future__ import annotations

import json as _json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from .. import db, deps
from ..auth.authorization_policy import check_agent_actor
from ..auth.error_handler_middleware import envelope
from ..deps import get_auth, get_event_bus, get_principal
from ..pubsub.domain_events import MatchCreated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["feed"])


# ── 공통 헬퍼 ──────────────────────────────────────────────────────────────

def _resolve_viewer_agent(agent_id: UUID, principal) -> object:
    """피드/탐색을 수행하는 viewer 에이전트 도메인 객체를 복원한다."""
    viewer_agent = next((a for a in principal.agents if a.agent_id == agent_id), None)
    if viewer_agent is None and deps.agent_service is not None:
        try:
            viewer_agent = deps.agent_service.get(agent_id)
        except KeyError:
            pass
    if viewer_agent is None:
        raise KeyError(f"에이전트 인스턴스를 찾을 수 없습니다: {agent_id}")
    return viewer_agent


def _build_cards(rows, viewer_agent, viewer_trust: float, already_swiped: set, sm) -> list[dict]:
    """후보 row 목록을 호환도 점수가 포함된 카드 목록으로 변환한다.

    이미 스와이프한 대상과 가시성 규칙(HIDDEN, trust<0.5 의 RESTRICTED)을 거른다.
    """
    from models.agent.agent_profile import AgentProfile
    from models.enums import VisibilityEnum

    cards: list[dict] = []
    for row in rows:
        cand_id = row["agent_id"]
        if cand_id in already_swiped:
            continue

        vis = str(row["visibility"]).upper()
        if vis == VisibilityEnum.HIDDEN.value:
            continue
        if vis == VisibilityEnum.RESTRICTED.value and viewer_trust < 0.5:
            continue

        # DB row에서 직접 AgentProfile 구성 — agent_service 인메모리 의존 제거
        compat_total, common_tags = 0.5, []
        try:
            style_vec = row["style_vector"]
            if isinstance(style_vec, str):
                style_vec = _json.loads(style_vec)
            cand_profile = AgentProfile(
                agent_id=cand_id,
                display_name=row["display_name"],
                visibility=VisibilityEnum(vis),
                capability_tags=list(row["capability_tags"] or []),
                style_vector=dict(style_vec or {}),
                tier_badge=row["tier_badge"],
                date_count=row["date_count"],
            )
            score = sm.getCompatibility(viewer_agent.getProfile(), cand_profile)
            compat_total = round(score.total, 3)
            common_tags = score.common_tags
        except Exception as exc:  # noqa: BLE001 — 점수 실패해도 카드는 노출(기본값 유지)
            logger.warning("compatibility 점수 계산 실패 agent_id=%s: %s", cand_id, exc)

        cards.append({
            "agent_id": str(cand_id),
            "display_name": row["display_name"],
            "avatar_url": row["avatar_url"],
            "tier_badge": row["tier_badge"],
            "trust_score": row["trust_score"],
            "compatibility_total": compat_total,
            "common_tags": common_tags,
        })
    return cards


def _paginate(results: list[dict], cursor: UUID | None, limit: int) -> tuple[list[dict], str | None]:
    """compatibility 정렬된 결과에 cursor 기반 페이지네이션을 적용한다.

    next_cursor 는 현재 페이지의 마지막 항목 id 이며, 다음 요청은 그 **다음** 항목부터
    시작한다(커서 항목 자신은 제외 → 중복 노출 방지). 커서를 찾지 못하면 빈 결과를 반환한다.
    """
    results.sort(key=lambda x: x["compatibility_total"], reverse=True)
    if cursor:
        idx = next((i for i, r in enumerate(results) if r["agent_id"] == str(cursor)), None)
        results = results[idx + 1:] if idx is not None else []
    page = results[:limit]
    next_cursor = page[-1]["agent_id"] if len(page) == limit else None
    return page, next_cursor


async def _load_already_swiped(agent_id: UUID) -> set:
    rows = await db.get_pool().fetch(
        "SELECT target_id FROM swipes WHERE agent_id = $1", agent_id
    )
    return {r["target_id"] for r in rows}


# ── Feed (추천) ────────────────────────────────────────────────────────────

@router.get("/{agent_id}/feed")
async def get_feed(
    agent_id: UUID,
    cursor: UUID | None = Query(None),
    limit: int = Query(20, le=50),
    principal=Depends(get_principal),
    ctx=Depends(get_auth),
) -> dict:
    agent_row = await db.get_agent_row(agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    check_agent_actor(ctx, agent_id, agent_row)

    viewer_agent = _resolve_viewer_agent(agent_id, principal)
    viewer_trust = viewer_agent.getTrustScore() or 0.0
    already_swiped = await _load_already_swiped(agent_id)

    sm = deps.score_manager
    assert sm is not None

    candidates = await db.get_all_visible_agents(exclude_agent_id=agent_id, exclude_principal_id=agent_row["principal_id"])
    results = _build_cards(candidates, viewer_agent, viewer_trust, already_swiped, sm)
    page, next_cursor = _paginate(results, cursor, limit)
    return envelope(data={"items": page, "next_cursor": next_cursor})


# ── Discover (필터 검색) ───────────────────────────────────────────────────

@router.get("/{agent_id}/discover")
async def discover(
    agent_id: UUID,
    q: str | None = Query(None, description="자유 텍스트 검색 (이름/bio/도메인)"),
    capability: str | None = Query(None, description="capability tag 필터 (comma-separated)"),
    trust_min: float | None = Query(None, alias="trustMin", ge=0.0, le=1.0),
    trust_max: float | None = Query(None, alias="trustMax", ge=0.0, le=1.0),
    style: str | None = Query(None, description="verbose|concise|formal|casual"),
    domain: str | None = Query(None, description="전문 도메인 필터"),
    availability: str | None = Query(None, description="available|busy|offline"),
    cursor: UUID | None = Query(None),
    limit: int = Query(24, le=50),
    principal=Depends(get_principal),
    ctx=Depends(get_auth),
) -> dict:
    agent_row = await db.get_agent_row(agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    check_agent_actor(ctx, agent_id, agent_row)

    viewer_agent = _resolve_viewer_agent(agent_id, principal)
    viewer_trust = viewer_agent.getTrustScore() or 0.0
    already_swiped = await _load_already_swiped(agent_id)

    sm = deps.score_manager
    assert sm is not None

    capability_tags = (
        [t.strip() for t in capability.split(",") if t.strip()] if capability else None
    )

    candidates = await db.get_agents_by_filters(
        agent_id,
        capability_tags=capability_tags,
        trust_min=trust_min,
        trust_max=trust_max,
        style=style,
        domain=domain,
        availability=availability,
        search_q=q,
    )
    results = _build_cards(candidates, viewer_agent, viewer_trust, already_swiped, sm)
    page, next_cursor = _paginate(results, cursor, limit)

    applied_filters = {
        k: v for k, v in {
            "q": q,
            "capability": capability_tags,
            "trustMin": trust_min,
            "trustMax": trust_max,
            "style": style,
            "domain": domain,
            "availability": availability,
        }.items() if v is not None
    }
    return envelope(data={
        "items": page,
        "next_cursor": next_cursor,
        "applied_filters": applied_filters,
    })


# ── Swipe ──────────────────────────────────────────────────────────────────

class SwipeRequest(BaseModel):
    target_id: UUID
    direction: str  # right | left | up


@router.post("/{agent_id}/swipe")
async def swipe(
    agent_id: UUID,
    body: SwipeRequest,
    principal=Depends(get_principal),
    bus=Depends(get_event_bus),
    ctx=Depends(get_auth),
) -> dict:
    agent_row = await db.get_agent_row(agent_id)
    if agent_row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    check_agent_actor(ctx, agent_id, agent_row)

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
