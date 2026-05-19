from __future__ import annotations

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


class UpdateAgentRequest(BaseModel):
    display_name: str | None = None
    visibility: str | None = None
    capability_tags: list[str] | None = None
    available_timezones: list[str] | None = None
    personality: dict | None = None
    llm_model: str | None = None
    avatar: str | None = None


@router.post("")
async def create_agent(body: CreateAgentRequest, principal=Depends(get_principal)) -> dict:
    agent, api_key = principal.createAgent(body.model_dump())
    profile = agent.getProfile()
    return envelope(data={
        "agent_id": str(agent.agent_id),
        "principal_id": str(agent.principal_id),
        "api_key": api_key,  # 단 1회 반환
        "display_name": profile.display_name,
        "visibility": profile.visibility.value if hasattr(profile.visibility, "value") else str(profile.visibility),
        "tier_badge": profile.tier_badge,
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
    return envelope(data={
        "agent_id": str(agent.agent_id),
        "display_name": profile.display_name,
        "visibility": profile.visibility.value if hasattr(profile.visibility, "value") else str(profile.visibility),
        "tier_badge": profile.tier_badge,
    })


@router.get("")
async def list_agents(principal=Depends(get_principal)) -> dict:
    rows = await db.get_principal_agents(principal.principal_id)
    return envelope(data=[{k: str(v) if isinstance(v, UUID) else v for k, v in dict(r).items()} for r in rows])
