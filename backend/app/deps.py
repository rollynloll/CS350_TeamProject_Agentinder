from __future__ import annotations

import json as _json
import os
import sys
from uuid import UUID

import asyncpg
from fastapi import Request

# models/ 는 프로젝트 루트에 위치 — sys.path 에 추가
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from models import AgentService, Principal, PrincipalProfile, ScoreManager
from models.agent.agent import Agent
from models.agent.agent_personality import AgentPersonality
from models.agent.agent_profile import AgentProfile
from models.enums import PlanEnum, VisibilityEnum
from models.llm.llm_client import LLMClient

from . import db
from .auth.auth_context import AuthContext
from .gateway.ws_gateway import WSGateway
from .pubsub.event_bus import EventBus

# ── 앱 전역 싱글톤 ────────────────────────────────────────────────────────
agent_service: AgentService | None = None
score_manager: ScoreManager | None = None
event_bus: EventBus | None = None
ws_gateway: WSGateway | None = None

# V1 인메모리 Principal 캐시 (결정 #5: lazy 재구성 + 캐시)
_principal_cache: dict[UUID, Principal] = {}


def init_singletons() -> None:
    global agent_service, score_manager, event_bus, ws_gateway
    agent_service = AgentService()
    score_manager = ScoreManager()
    event_bus = EventBus()
    ws_gateway = WSGateway()

    event_bus.subscribe("MatchCreated", ws_gateway.on_domain_event)
    event_bus.subscribe("DateProposed", ws_gateway.on_domain_event)
    event_bus.subscribe("DateStarted", ws_gateway.on_domain_event)
    event_bus.subscribe("DateEnded", ws_gateway.on_domain_event)
    event_bus.subscribe("MessageCreated", ws_gateway.on_domain_event)


# ── FastAPI Depends 헬퍼 ─────────────────────────────────────────────────

def get_event_bus() -> EventBus:
    assert event_bus is not None
    return event_bus


def get_ws_gateway() -> WSGateway:
    assert ws_gateway is not None
    return ws_gateway


def get_auth(request: Request) -> AuthContext:
    return request.state.auth


def reconstruct_agent_from_row(row: asyncpg.Record) -> Agent:
    """DB 레코드로부터 Agent 도메인 객체를 재구성한다."""
    style_sliders: dict[str, float] = {}
    if row["style_formal"] is not None:
        style_sliders["formal"] = row["style_formal"] / 100.0
    if row["style_verbose"] is not None:
        style_sliders["verbose"] = row["style_verbose"] / 100.0
    if row["style_bold"] is not None:
        style_sliders["bold"] = row["style_bold"] / 100.0

    surface: dict = {"bio": row["bio"] or "", "style_sliders": style_sliders}
    deep: dict = {}
    if row["thinking_style"]:
        deep["thinking_style"] = row["thinking_style"]
    if row["values"]:
        deep["values"] = [v.strip() for v in row["values"].split(",")]
    if row["conflict_style"]:
        deep["conflict_handling"] = row["conflict_style"]

    aspiration: dict = {}
    if row["collaboration_goal"]:
        aspiration["collaboration_goals"] = [g.strip() for g in row["collaboration_goal"].split(",")]
    if row["domain_interest"]:
        aspiration["interest_domains"] = [d.strip() for d in row["domain_interest"].split(",")]

    personality = AgentPersonality(
        surface=surface,
        deep=deep,
        aspiration=aspiration,
        system_prompt_cache=row["system_prompt_cache"] or None,
    )

    style_vec = row["style_vector"]
    if isinstance(style_vec, str):
        style_vec = _json.loads(style_vec)
    style_vec = dict(style_vec or {})

    profile = AgentProfile(
        agent_id=row["agent_id"],
        display_name=row["display_name"],
        avatar=row["avatar_url"] or "",
        visibility=VisibilityEnum(str(row["visibility"]).upper()),
        capability_tags=list(row["capability_tags"] or []),
        style_vector=style_vec,
        available_timezones=list(row["available_timezones"] or []),
        tier_badge=row["tier_badge"],
        date_count=row["date_count"],
    )

    llm_model = row["llm_model"] if "llm_model" in row.keys() else "gpt-4o"
    llm_client = LLMClient(model=llm_model or "gpt-4o")

    agent = Agent(
        agent_id=row["agent_id"],
        principal_id=row["principal_id"],
        profile=profile,
        personality=personality,
        llm_client=llm_client,
    )
    llm_client.agent = agent

    if row["trust_score"] is not None:
        agent.updateTrustScore(row["trust_score"])

    return agent


async def get_principal_by_id(principal_id: UUID) -> Principal:
    """principal_id로 Principal을 반환한다. 캐시 miss 시 DB에서 재구성."""
    if principal_id in _principal_cache:
        return _principal_cache[principal_id]

    row = await db.get_principal_row(principal_id)
    if row is None:
        raise KeyError(f"Principal을 찾을 수 없습니다: {principal_id}")

    profile = PrincipalProfile(
        email=row["email"],
        name=row["name"],
        plan=PlanEnum(row["plan"].upper()),
    )
    assert agent_service is not None
    assert score_manager is not None
    principal = Principal(
        principal_id=principal_id,
        profile=profile,
        agent_service=agent_service,
        score_manager=score_manager,
        created_at=row["created_at"],
    )

    agent_rows = await db.get_principal_agents_full(principal_id)
    for agent_row in agent_rows:
        agent = reconstruct_agent_from_row(agent_row)
        principal._agents[agent.agent_id] = agent
        agent_service._agents[agent.agent_id] = agent
        agent_service._principal_agents.setdefault(principal_id, [])
        if agent.agent_id not in agent_service._principal_agents[principal_id]:
            agent_service._principal_agents[principal_id].append(agent.agent_id)

    _principal_cache[principal_id] = principal
    return principal


async def get_principal(request: Request) -> Principal:
    ctx: AuthContext = request.state.auth
    pid = ctx.principal_id
    assert pid is not None
    return await get_principal_by_id(pid)
