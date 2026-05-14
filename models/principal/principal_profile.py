from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..enums import PlanEnum

if TYPE_CHECKING:
    pass

_MAX_AGENTS_BY_PLAN = {
    PlanEnum.FREE: 5,
    PlanEnum.PREMIUM: 20,
}


@dataclass
class PrincipalProfile:
    """Mutable information about a principal (human owner).

    agentCount and maxAgents are computed values, not DB columns.
    """
    email: str
    name: str
    plan: PlanEnum = PlanEnum.FREE
    mfa_enabled: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------ #
    # Computed properties (not persisted)                                   #
    # ------------------------------------------------------------------ #

    @property
    def max_agents(self) -> int:
        return _MAX_AGENTS_BY_PLAN[self.plan]

    def agent_count(self, agents: list) -> int:
        return len(agents)

    # ------------------------------------------------------------------ #

    def can_add_agent(self, current_agent_count: int) -> bool:
        return current_agent_count < self.max_agents

    def is_mfa_enabled(self) -> bool:
        return self.mfa_enabled

    def update(self, fields: dict) -> None:
        allowed = {"email", "name", "plan", "mfa_enabled"}
        for key, value in fields.items():
            if key in allowed:
                setattr(self, key, value)
        self.updated_at = datetime.now(timezone.utc)
