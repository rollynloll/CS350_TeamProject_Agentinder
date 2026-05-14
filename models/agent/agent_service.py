from __future__ import annotations

import asyncio
import hashlib
import secrets
from typing import TYPE_CHECKING, Dict, Optional, Tuple
from uuid import UUID, uuid4

from ..enums import PlanEnum
from .agent import Agent
from .agent_personality import AgentPersonality
from .agent_profile import AgentProfile

if TYPE_CHECKING:
    from ..llm.llm_client import LLMClient

_MAX_AGENTS: Dict[PlanEnum, int] = {
    PlanEnum.FREE: 5,
    PlanEnum.PREMIUM: 20,
}

_CREDENTIAL_BYTES = 32


class AgentService:
    """Orchestrates agent lifecycle: create, update, get.

    Operates on an in-memory store. In production, replace _agents and
    _credentials dict operations with Supabase/DB calls.
    """

    def __init__(self) -> None:
        # agent_id → Agent
        self._agents: Dict[UUID, Agent] = {}
        # principal_id → list of agent_ids
        self._principal_agents: Dict[UUID, list[UUID]] = {}
        # agent_id → credential hash (plaintext never stored)
        self._credentials: Dict[UUID, str] = {}
        # Used to create LLMClients — injected so tests can swap it
        self._default_llm_model: str = "gpt-4o"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        principal_id: UUID,
        profile_data: dict,
        plan: PlanEnum = PlanEnum.FREE,
    ) -> Tuple[Agent, str]:
        """Creates a new agent. Returns (agent, plaintext_api_key).

        The plaintext API key is returned exactly once and never stored.
        """
        # 1. Agent count limit
        existing = self._principal_agents.get(principal_id, [])
        max_agents = _MAX_AGENTS[plan]
        if len(existing) >= max_agents:
            raise PermissionError(
                f"Agent limit reached ({max_agents}) for plan {plan.value}"
            )

        # 2. Duplicate display name check
        display_name = profile_data.get("display_name", "")
        if display_name and self._is_name_taken(principal_id, display_name):
            raise ValueError(f"Agent name '{display_name}' is already in use")

        # 3. Build personality
        personality_data = profile_data.pop("personality", {})
        personality = AgentPersonality(
            surface=personality_data.get("surface", {}),
            deep=personality_data.get("deep", {}),
            aspiration=personality_data.get("aspiration", {}),
        )
        personality.system_prompt_cache = personality._build_system_prompt()

        # 4. Build profile (style_vector mirrors personality surface sliders)
        agent_id = uuid4()
        style_vector = personality.surface.get("style_sliders", {})
        profile = AgentProfile(
            agent_id=agent_id,
            display_name=display_name,
            avatar=profile_data.get("avatar", ""),
            visibility=profile_data.get("visibility", AgentProfile.__dataclass_fields__["visibility"].default),
            capability_tags=profile_data.get("capability_tags", []),
            style_vector=style_vector,
            available_timezones=profile_data.get("available_timezones", []),
        )

        # 5. Build LLMClient
        llm_model = profile_data.get("llm_model", self._default_llm_model)
        llm_client = self._build_llm_client(llm_model)

        # 6. Create Agent
        agent = Agent(
            agent_id=agent_id,
            principal_id=principal_id,
            profile=profile,
            personality=personality,
            llm_client=llm_client,
        )
        llm_client.agent = agent  # back-reference so LLMClient can call agent.getPersonality()

        # 7. Generate API credential (hash stored, plaintext returned once)
        plaintext_key = secrets.token_urlsafe(_CREDENTIAL_BYTES)
        key_hash = self._hash_key(plaintext_key)
        self._credentials[agent_id] = key_hash

        # 8. Persist in memory
        self._agents[agent_id] = agent
        self._principal_agents.setdefault(principal_id, []).append(agent_id)

        # 9. Kick off async embedding computation (non-blocking)
        self._schedule_embedding(agent)

        return agent, plaintext_key

    def update(
        self,
        agent_id: UUID,
        principal_id: UUID,
        profile_data: dict,
    ) -> Agent:
        """Updates an agent. Only the owning principal may update."""
        agent = self._get_or_raise(agent_id)

        # 1. Ownership check
        if agent.principal_id != principal_id:
            raise PermissionError("Only the owning principal can update this agent")

        # 2. Personality changes
        personality_data = profile_data.pop("personality", None)
        if personality_data is not None:
            agent.setPersonality(personality_data)
            # system_prompt_cache regenerated inside setPersonality → AgentPersonality.update()

        # 3. Capability tags change → async embedding recompute
        if "capability_tags" in profile_data:
            agent.setProfile({"capability_tags": profile_data.pop("capability_tags")})
            self._schedule_embedding(agent)

        # 4. LLM model change → rebuild LLMClient
        if "llm_model" in profile_data:
            new_model = profile_data.pop("llm_model")
            new_client = self._build_llm_client(new_model)
            new_client.agent = agent
            agent.setLLMClient(new_client)

        # 5. Remaining profile fields
        if profile_data:
            agent.setProfile(profile_data)

        return agent

    def get(self, agent_id: UUID) -> Agent:
        return self._get_or_raise(agent_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_raise(self, agent_id: UUID) -> Agent:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent {agent_id} not found")
        return agent

    def _is_name_taken(self, principal_id: UUID, display_name: str) -> bool:
        for aid in self._principal_agents.get(principal_id, []):
            agent = self._agents.get(aid)
            if agent and agent.getProfile().display_name == display_name:
                return True
        return False

    def _build_llm_client(self, model: str) -> LLMClient:
        from ..llm.llm_client import LLMClient
        return LLMClient(model=model)

    @staticmethod
    def _hash_key(plaintext: str) -> str:
        return hashlib.sha256(plaintext.encode()).hexdigest()

    def _schedule_embedding(self, agent: Agent) -> None:
        """Attaches embedding computation to the running loop, if one exists."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._compute_embedding_async(agent))
        except RuntimeError:
            pass  # No running event loop — embedding stays None until explicitly computed

    async def _compute_embedding_async(self, agent: Agent) -> None:
        """Computes and stores capability_embedding without blocking the caller."""
        llm_client = agent.getLLMClient()
        if llm_client is None:
            return
        profile = agent.getProfile()
        tags = profile.capability_tags
        if not tags:
            return
        embedding = await llm_client.embed(", ".join(tags))
        agent.setProfile({"capability_embedding": embedding})
