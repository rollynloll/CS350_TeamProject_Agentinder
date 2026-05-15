from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from ..enums import VisibilityEnum

_NEW_AGENT_DATE_THRESHOLD = 5


@dataclass
class AgentProfile:
    """Mutable display and capability information for an agent.

    capability_tags and capability_embedding live here (not in AgentPersonality)
    because they are used for feed ranking and compatibility scoring.
    style_vector mirrors AgentPersonality.surface['style_sliders'] and is kept
    in sync by AgentService whenever personality is updated.
    """
    agent_id: UUID
    display_name: str
    avatar: str = ""
    visibility: VisibilityEnum = VisibilityEnum.PUBLIC
    capability_tags: List[str] = field(default_factory=list)
    capability_embedding: Optional[List[float]] = None
    # Keys are slider names (e.g. "formality", "creativity"); values 0.0–1.0
    style_vector: Dict[str, float] = field(default_factory=dict)
    available_timezones: List[str] = field(default_factory=list)
    # 'new_agent' when date_count < 5, else str(tier_int)
    tier_badge: str = "new_agent"
    date_count: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_new_agent(self) -> bool:
        return self.date_count < _NEW_AGENT_DATE_THRESHOLD

    def update(self, fields: dict) -> None:
        allowed = {
            "display_name", "avatar", "visibility", "capability_tags",
            "capability_embedding", "style_vector", "available_timezones",
            "tier_badge", "date_count",
        }
        for key, value in fields.items():
            if key in allowed:
                setattr(self, key, value)
        self.updated_at = datetime.now(timezone.utc)
