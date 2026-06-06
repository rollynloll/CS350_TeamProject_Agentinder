from __future__ import annotations

import json as _json
import logging
import random
from typing import Optional
from uuid import UUID

from models.agent.agent_profile import AgentProfile
from models.date.date_session import DateSession
from models.enums import SwipeEnum, VisibilityEnum
from models.matching.matching_service import IMatchingService

from .. import db, deps
from ..deps import reconstruct_agent_from_row
from ..pubsub.domain_events import MatchCreated

logger = logging.getLogger(__name__)


class MatchingServiceImpl(IMatchingService):
    """IMatchingService 구현체 (A팀).

    runAsyncMatch  : 백그라운드 스케줄러 → 랜덤 선택, skipTrustCheck=True
    runAiMatch     : API 요청 → compat 최고점 선택, skipTrustCheck=False
    runSelectMatch : 피드 스와이프 → mutual 확인, skipTrustCheck=False
    """

    def __init__(self, bus) -> None:
        self._bus = bus

    @property
    def _sm(self):
        assert deps.score_manager is not None
        return deps.score_manager

    # ------------------------------------------------------------------
    # IMatchingService 구현
    # ------------------------------------------------------------------

    async def runAsyncMatch(self, agent_id: UUID) -> Optional[DateSession]:
        row = await db.get_agent_full(agent_id)
        if row is None:
            return None

        already_matched = await _get_matched_partner_ids(agent_id)

        candidates = await db.get_all_visible_agents(
            exclude_agent_id=agent_id,
            exclude_principal_id=row["principal_id"],
        )
        # auto_match=true 상대만 선택 (동의 없는 에이전트에게 강제 데이트 방지)
        eligible = [
            c for c in candidates
            if c.get("auto_match") and c["agent_id"] not in already_matched
        ]
        if not eligible:
            return None

        cand = random.choice(eligible)
        cand_id: UUID = cand["agent_id"]

        await db.insert_swipe(agent_id, cand_id, "right")
        a, b = sorted([agent_id, cand_id], key=str)
        match_row = await db.insert_match(a, b)
        if match_row is None:
            return None  # 이미 존재하는 매치

        self._bus.publish(MatchCreated(
            match_id=match_row["match_id"],
            agent_a_id=a,
            agent_b_id=b,
            principal_a_id=row["principal_id"],
            principal_b_id=cand["principal_id"],
        ))
        logger.info("async-match 매치 생성: %s <-> %s", agent_id, cand_id)

        agent_a = reconstruct_agent_from_row(row)
        cand_row = await db.get_agent_full(cand_id)
        if cand_row is None:
            return None
        agent_b = reconstruct_agent_from_row(cand_row)

        return DateSession(
            agent_a=agent_a,
            agent_b=agent_b,
            match_id=match_row["match_id"],
            skip_trust_check=True,
            topic=None,
            score_manager=self._sm,
        )

    async def runAiMatch(self, agent_id: UUID, topic: str) -> Optional[DateSession]:
        row = await db.get_agent_full(agent_id)
        if row is None:
            return None

        agent_a = reconstruct_agent_from_row(row)
        candidates = await db.get_all_visible_agents(
            exclude_agent_id=agent_id,
            exclude_principal_id=row["principal_id"],
        )
        if not candidates:
            return None

        best_cand = None
        best_score = -1.0
        for cand in candidates:
            try:
                style_vec = cand["style_vector"]
                if isinstance(style_vec, str):
                    style_vec = _json.loads(style_vec)
                cand_profile = AgentProfile(
                    agent_id=cand["agent_id"],
                    display_name=cand["display_name"],
                    visibility=VisibilityEnum(str(cand["visibility"]).upper()),
                    capability_tags=list(cand["capability_tags"] or []),
                    style_vector=dict(style_vec or {}),
                    tier_badge=cand["tier_badge"],
                    date_count=cand["date_count"],
                )
                score = self._sm.getCompatibility(agent_a.getProfile(), cand_profile).total
                if score > best_score:
                    best_score = score
                    best_cand = cand
            except Exception:
                logger.warning("ai-match: compat 계산 실패 cand=%s", cand["agent_id"])
                continue

        if best_cand is None:
            return None

        cand_id: UUID = best_cand["agent_id"]
        await db.insert_swipe(agent_id, cand_id, "right")

        a, b = sorted([agent_id, cand_id], key=str)
        match_row = await db.insert_match(a, b)
        if match_row is None:
            return None

        self._bus.publish(MatchCreated(
            match_id=match_row["match_id"],
            agent_a_id=a,
            agent_b_id=b,
            principal_a_id=row["principal_id"],
            principal_b_id=best_cand["principal_id"],
        ))

        cand_row = await db.get_agent_full(cand_id)
        if cand_row is None:
            return None
        agent_b = reconstruct_agent_from_row(cand_row)

        return DateSession(
            agent_a=agent_a,
            agent_b=agent_b,
            match_id=match_row["match_id"],
            skip_trust_check=False,
            topic=topic,
            score_manager=self._sm,
        )

    async def runSelectMatch(
        self,
        agent_id: UUID,
        target_id: UUID,
        action: SwipeEnum,
        topic: str,
    ) -> Optional[DateSession]:
        if action == SwipeEnum.LEFT:
            await db.insert_swipe(agent_id, target_id, "left")
            return None

        direction = "up" if action == SwipeEnum.UP else "right"
        await db.insert_swipe(agent_id, target_id, direction)

        counter = await db.get_counter_swipe(agent_id, target_id)
        if not counter:
            return None

        a, b = sorted([agent_id, target_id], key=str)
        match_row = await db.insert_match(a, b)
        if match_row is None:
            return None

        row_a = await db.get_agent_full(agent_id)
        row_b = await db.get_agent_full(target_id)
        if row_a is None or row_b is None:
            return None

        agent_a = reconstruct_agent_from_row(row_a)
        agent_b = reconstruct_agent_from_row(row_b)

        self._bus.publish(MatchCreated(
            match_id=match_row["match_id"],
            agent_a_id=a,
            agent_b_id=b,
            principal_a_id=row_a["principal_id"],
            principal_b_id=row_b["principal_id"],
        ))

        return DateSession(
            agent_a=agent_a,
            agent_b=agent_b,
            match_id=match_row["match_id"],
            skip_trust_check=False,
            topic=topic,
            score_manager=self._sm,
        )


# ------------------------------------------------------------------
# 내부 헬퍼
# ------------------------------------------------------------------

async def _get_matched_partner_ids(agent_id: UUID) -> set[UUID]:
    rows = await db.get_pool().fetch(
        "SELECT CASE WHEN agent_a_id = $1 THEN agent_b_id ELSE agent_a_id END AS partner_id"
        " FROM matches WHERE agent_a_id = $1 OR agent_b_id = $1",
        agent_id,
    )
    return {r["partner_id"] for r in rows}
