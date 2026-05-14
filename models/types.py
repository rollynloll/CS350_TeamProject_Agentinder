from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class Match:
    """Stub type — full match lifecycle owned by Team A (backend)."""
    match_id: UUID = field(default_factory=uuid4)
    agent_a_id: UUID = field(default_factory=uuid4)
    agent_b_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
