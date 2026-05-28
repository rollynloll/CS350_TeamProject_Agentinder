from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MatchCreated(DomainEvent):
    match_id: UUID = field(default_factory=uuid4)
    agent_a_id: UUID = field(default_factory=uuid4)
    agent_b_id: UUID = field(default_factory=uuid4)
    principal_a_id: UUID | None = None
    principal_b_id: UUID | None = None


@dataclass
class DateProposed(DomainEvent):
    date_id: UUID = field(default_factory=uuid4)
    match_id: UUID = field(default_factory=uuid4)
    proposer_principal_id: UUID | None = None
    target_principal_id: UUID | None = None


@dataclass
class DateStarted(DomainEvent):
    date_id: UUID = field(default_factory=uuid4)
    match_id: UUID = field(default_factory=uuid4)


@dataclass
class DateEnded(DomainEvent):
    date_id: UUID = field(default_factory=uuid4)
    match_id: UUID = field(default_factory=uuid4)
    outcome: str | None = None


@dataclass
class MessageCreated(DomainEvent):
    message_id: UUID = field(default_factory=uuid4)
    match_id: UUID = field(default_factory=uuid4)
    sender_agent_id: UUID = field(default_factory=uuid4)
    content: str = ""
