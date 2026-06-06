from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class Match:
    """매치 로그 객체 — 상태 머신 없음, 비즈니스 메서드 없음.

    Full match lifecycle (DB INSERT, swipe handling) is owned by Team A.
    Team B owns the helper queries and unmatched_at field.
    """
    match_id: UUID = field(default_factory=uuid4)
    agent_a_id: UUID = field(default_factory=uuid4)
    agent_b_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    unmatched_at: Optional[datetime] = None

    def has_agent(self, agent_id: UUID) -> bool:
        return agent_id in (self.agent_a_id, self.agent_b_id)

    def other_agent_id(self, agent_id: UUID) -> UUID:
        if agent_id == self.agent_a_id:
            return self.agent_b_id
        if agent_id == self.agent_b_id:
            return self.agent_a_id
        raise ValueError(f"Agent {agent_id} is not part of match {self.match_id}")
