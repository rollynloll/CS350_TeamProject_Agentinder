from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import db
from ..auth.error_handler_middleware import envelope
from ..deps import get_principal

router = APIRouter(prefix="/v1/agents", tags=["agents"])


class CreateAgentRequest(BaseModel):
    display_name: str
    visibility: str = "PUBLIC"
    capability_tags: list[str] = []
    available_timezones: list[str] = []
    personality: dict = {}
    llm_model: str = "gpt-4o"
    avatar: str = ""
    auto_match: bool = False
    task_description: str = ""


class UpdateAgentRequest(BaseModel):
    display_name: str | None = None
    visibility: str | None = None
    capability_tags: list[str] | None = None
    available_timezones: list[str] | None = None
    personality: dict | None = None
    llm_model: str | None = None
    avatar: str | None = None
    auto_match: bool | None = None
    task_description: str | None = None


def _personality_to_db(personality) -> dict:
    surface = personality.surface
    deep = personality.deep
    aspiration = personality.aspiration
    sliders = surface.get("style_sliders", {})
    return {
        "bio": surface.get("bio", ""),
        "style_formal": int(sliders.get("formal", 0.5) * 100),
        "style_verbose": int(sliders.get("verbose", 0.5) * 100),
        "style_bold": int(sliders.get("bold", 0.5) * 100),
        "thinking_style": deep.get("thinking_style"),
        "values_text": ",".join(deep.get("values", [])) if deep.get("values") else None,
        "conflict_style": deep.get("conflict_handling"),
        "collaboration_goal": ",".join(aspiration.get("collaboration_goals", [])) if aspiration.get("collaboration_goals") else None,
        "domain_interest": ",".join(aspiration.get("interest_domains", [])) if aspiration.get("interest_domains") else None,
        "system_prompt_cache": personality.system_prompt_cache or "",
    }


@router.post("")
async def create_agent(body: CreateAgentRequest, principal=Depends(get_principal)) -> dict:
    agent, api_key = principal.createAgent(body.model_dump())
    profile = agent.getProfile()
    personality = agent.getPersonality()

    vis = profile.visibility.value if hasattr(profile.visibility, "value") else str(profile.visibility)
    pf = _personality_to_db(personality)

    await db.insert_agent_full(
        agent_id=agent.agent_id,
        principal_id=agent.principal_id,
        display_name=profile.display_name,
        avatar_url=profile.avatar or "",
        visibility=vis,
        llm_model=body.llm_model or "gpt-4o",
        style_vector=profile.style_vector,
        available_timezones=profile.available_timezones,
        api_key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
        auto_match=body.auto_match,
        task_description=body.task_description,
        **pf,
    )
    if profile.capability_tags:
        await db.sync_capability_tags(agent.agent_id, profile.capability_tags)

    return envelope(data={
        "agent_id": str(agent.agent_id),
        "principal_id": str(agent.principal_id),
        "api_key": api_key,
        "display_name": profile.display_name,
        "visibility": vis,
        "tier_badge": profile.tier_badge,
        "auto_match": body.auto_match,
        "task_description": body.task_description,
    })


@router.get("/{agent_id}")
async def get_profile(agent_id: UUID) -> dict:
    row = await db.get_agent_row(agent_id)
    if row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    return envelope(data={k: str(v) if isinstance(v, UUID) else v for k, v in dict(row).items()})


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: UUID,
    body: UpdateAgentRequest,
    principal=Depends(get_principal),
) -> dict:
    row = await db.get_agent_row(agent_id)
    if row is None:
        raise KeyError(f"에이전트를 찾을 수 없습니다: {agent_id}")
    if row["principal_id"] != principal.principal_id:
        raise PermissionError("이 에이전트의 소유자가 아닙니다.")

    profile_data = {k: v for k, v in body.model_dump().items() if v is not None}
    agent = principal.updateAgent(agent_id, profile_data)
    profile = agent.getProfile()
    personality = agent.getPersonality()

    vis = profile.visibility.value if hasattr(profile.visibility, "value") else str(profile.visibility)
    pf = _personality_to_db(personality)

    resolved_auto_match = body.auto_match if body.auto_match is not None else bool(row.get("auto_match", False))
    resolved_task_description = body.task_description if body.task_description is not None else (row.get("task_description") or "")

    await db.upsert_agent_profile_row(
        agent_id=agent.agent_id,
        display_name=profile.display_name,
        avatar_url=profile.avatar or "",
        visibility=vis,
        llm_model=body.llm_model or row["llm_model"] or "gpt-4o",
        style_vector=profile.style_vector,
        available_timezones=profile.available_timezones,
        auto_match=resolved_auto_match,
        task_description=resolved_task_description,
        **pf,
    )
    if body.capability_tags is not None:
        await db.sync_capability_tags(agent.agent_id, body.capability_tags)

    return envelope(data={
        "agent_id": str(agent.agent_id),
        "display_name": profile.display_name,
        "visibility": vis,
        "tier_badge": profile.tier_badge,
        "auto_match": resolved_auto_match,
        "task_description": resolved_task_description,
    })


@router.get("")
async def list_agents(principal=Depends(get_principal)) -> dict:
    rows = await db.get_principal_agents(principal.principal_id)
    return envelope(data=[{k: str(v) if isinstance(v, UUID) else v for k, v in dict(r).items()} for r in rows])
