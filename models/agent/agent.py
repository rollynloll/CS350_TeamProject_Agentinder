from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from uuid import UUID, uuid4

from ..enums import SwipeEnum, VisibilityEnum
from ..types import Match

if TYPE_CHECKING:
    from ..llm.llm_client import LLMClient
    from .agent_personality import AgentPersonality
    from .agent_profile import AgentProfile

_RESTRICTED_TRUST_THRESHOLD = 0.5


class Agent:
    """Core domain object representing an AI agent.

    Immutable identity: agent_id, principal_id, created_at
    Mutable state:      profile, personality (single-owned), llm_client, trust_score_cache
    """

    def __init__(
        self,
        agent_id: UUID,
        principal_id: UUID,
        profile: AgentProfile,
        personality: AgentPersonality,
        llm_client: Optional[LLMClient] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self._agent_id: UUID = agent_id
        self._principal_id: UUID = principal_id
        self._created_at: datetime = created_at or datetime.now(timezone.utc)
        self._profile: AgentProfile = profile
        self._personality: AgentPersonality = personality
        self._llm_client: Optional[LLMClient] = llm_client
        self._trust_score: Optional[float] = None  # cache; source of truth in ScoreManager
        self._active_date_ids: List[UUID] = []

    # ------------------------------------------------------------------ #
    # Getters                                                               #
    # ------------------------------------------------------------------ #

    @property
    def agent_id(self) -> UUID:
        return self._agent_id

    @property
    def principal_id(self) -> UUID:
        return self._principal_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def getProfile(self, fields: Optional[List[str]] = None) -> Union[AgentProfile, dict]:
        if fields is None:
            return self._profile
        return {f: getattr(self._profile, f) for f in fields if hasattr(self._profile, f)}

    def getPersonality(
        self, fields: Optional[List[str]] = None
    ) -> Union[AgentPersonality, dict]:
        if fields is None:
            return self._personality
        return {
            f: getattr(self._personality, f)
            for f in fields
            if hasattr(self._personality, f)
        }

    def getLLMClient(self) -> Optional[LLMClient]:
        return self._llm_client

    def getTrustScore(self) -> Optional[float]:
        return self._trust_score

    def getPrincipalId(self) -> UUID:
        return self._principal_id

    # ------------------------------------------------------------------ #
    # Setters                                                               #
    # ------------------------------------------------------------------ #

    def setProfile(self, fields: dict) -> None:
        self._profile.update(fields)

    def setPersonality(self, fields: dict) -> None:
        self._personality.update(fields)
        # style_vector in profile must stay in sync with personality surface sliders
        sliders = self._personality.surface.get("style_sliders")
        if sliders is not None:
            self._profile.update({"style_vector": sliders})

    def setLLMClient(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def updateTrustScore(self, score: float) -> None:
        self._trust_score = score

    # ------------------------------------------------------------------ #
    # Business logic                                                        #
    # ------------------------------------------------------------------ #

    def isActive(self) -> bool:
        return len(self._active_date_ids) > 0

    def isVisibleTo(self, trust_score: float) -> bool:
        vis = self._profile.visibility
        if vis == VisibilityEnum.PUBLIC:
            return True
        if vis == VisibilityEnum.RESTRICTED:
            return trust_score >= _RESTRICTED_TRUST_THRESHOLD
        # HIDDEN — only reachable via direct invite, never via feed
        return False

    def isNewAgent(self) -> bool:
        return self._profile.is_new_agent()

    def joinDate(self, date_id: UUID) -> None:
        if date_id not in self._active_date_ids:
            self._active_date_ids.append(date_id)

    def leaveDate(self, date_id: UUID) -> None:
        if date_id in self._active_date_ids:
            self._active_date_ids.remove(date_id)
            self._profile.date_count += 1
            self._update_tier_badge()

    def swipe(self, target_id: UUID, direction: SwipeEnum) -> Optional[Match]:
        """Records a swipe. Mutual RIGHT/UP creates a Match (stub logic)."""
        if direction == SwipeEnum.LEFT:
            return None
        # Actual match-creation logic lives in Team A's backend.
        # Return a stub Match so the interface contract is fulfilled.
        return Match(agent_a_id=self._agent_id, agent_b_id=target_id)

    def sendMessage(self, match_id: UUID, content: str) -> str:
        """Generates a personality-consistent response via LLMClient."""
        if self._llm_client is None:
            raise RuntimeError(
                f"Agent {self._agent_id} has no LLMClient attached"
            )
        # History management is owned by the caller (Team A).
        # We pass an empty history here; in practice the caller supplies it.
        from ..types import Message
        history: List[Message] = [Message(role="user", content=content)]
        return self._llm_client.generate(history=history, turn_count=1)

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _update_tier_badge(self) -> None:
        if self._profile.date_count < 5:
            self._profile.tier_badge = "new_agent"
        else:
            self._profile.tier_badge = str(self._profile.date_count)
