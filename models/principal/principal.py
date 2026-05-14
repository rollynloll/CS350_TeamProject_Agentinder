from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from ..agent.agent import Agent
from ..agent.agent_service import AgentService
from ..enums import PlanEnum
from ..rating.rating import Rating
from ..score.score_manager import ScoreManager
from .principal_profile import PrincipalProfile


class Principal:
    """Human owner of one or more agents.

    Delegates agent lifecycle to AgentService and score updates to ScoreManager.
    """

    def __init__(
        self,
        principal_id: UUID,
        profile: PrincipalProfile,
        agent_service: AgentService,
        score_manager: ScoreManager,
        created_at: Optional[datetime] = None,
    ) -> None:
        self._principal_id: UUID = principal_id
        self._profile: PrincipalProfile = profile
        self._agent_service: AgentService = agent_service
        self._score_manager: ScoreManager = score_manager
        self._created_at: datetime = created_at or datetime.now(timezone.utc)
        # agent_id → Agent (live references after creation)
        self._agents: Dict[UUID, Agent] = {}

    # ------------------------------------------------------------------ #
    # Properties                                                            #
    # ------------------------------------------------------------------ #

    @property
    def principal_id(self) -> UUID:
        return self._principal_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def profile(self) -> PrincipalProfile:
        return self._profile

    @property
    def agents(self) -> List[Agent]:
        return list(self._agents.values())

    # ------------------------------------------------------------------ #
    # Profile                                                               #
    # ------------------------------------------------------------------ #

    def updateProfile(self, fields: dict) -> None:
        self._profile.update(fields)

    # ------------------------------------------------------------------ #
    # Agent management                                                      #
    # ------------------------------------------------------------------ #

    def createAgent(self, profile_data: dict) -> tuple[Agent, str]:
        """Creates a new agent under this principal.

        Returns (agent, plaintext_api_key). The API key is shown exactly once.
        """
        if not self._profile.can_add_agent(len(self._agents)):
            raise PermissionError(
                f"Cannot create more agents: limit is {self._profile.max_agents} "
                f"for plan {self._profile.plan.value}"
            )
        agent, api_key = self._agent_service.create(
            principal_id=self._principal_id,
            profile_data=profile_data,
            plan=self._profile.plan,
        )
        self._agents[agent.agent_id] = agent
        return agent, api_key

    def updateAgent(self, agent_id: UUID, profile_data: dict) -> Agent:
        agent = self._agent_service.update(
            agent_id=agent_id,
            principal_id=self._principal_id,
            profile_data=profile_data,
        )
        return agent

    # ------------------------------------------------------------------ #
    # Match management (stubs — full logic in Team A)                       #
    # ------------------------------------------------------------------ #

    def approveMatch(self, match_id: UUID) -> None:
        """Signals approval of a proposed match. Team A owns match state."""

    def rejectMatch(self, match_id: UUID) -> None:
        """Signals rejection of a proposed match. Team A owns match state."""

    # ------------------------------------------------------------------ #
    # Rating submission                                                     #
    # ------------------------------------------------------------------ #

    def submitRating(self, date_id: UUID, rating: Rating) -> None:
        """Submits a post-date rating and propagates it to the trust score."""
        data_point = rating.to_trust_data_point()
        self._score_manager.addTrustDataPoint(rating.rated_agent_id, data_point)

        # Refresh the rated agent's cached trust score if it's one of ours.
        # In practice, any agent can be rated — the ScoreManager owns the scores.
        new_score = self._score_manager.getTrust(rating.rated_agent_id)
        if new_score is not None and rating.rated_agent_id in self._agents:
            self._agents[rating.rated_agent_id].updateTrustScore(new_score)
