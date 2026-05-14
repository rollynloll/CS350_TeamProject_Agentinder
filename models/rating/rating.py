from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from ..enums import IssueEnum

if TYPE_CHECKING:
    from ..score.score_manager import TrustDataPoint

EDIT_WINDOW_SECONDS = 72 * 3600


@dataclass
class Rating:
    date_id: UUID
    rater_principal_id: UUID
    rated_agent_id: UUID
    stars: int                      # 1–5
    compatibility: float            # 0.0–1.0
    comments: str = ""
    issues: List[IssueEnum] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_locked: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.stars <= 5:
            raise ValueError("stars must be between 1 and 5")
        if not 0.0 <= self.compatibility <= 1.0:
            raise ValueError("compatibility must be between 0.0 and 1.0")

    def _check_editable(self) -> None:
        if self.is_locked:
            raise PermissionError("Rating is locked and cannot be modified")
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        if elapsed > EDIT_WINDOW_SECONDS:
            self.is_locked = True
            raise PermissionError("Rating can only be modified within 72 hours of creation")

    def update(self, fields: dict) -> None:
        self._check_editable()
        allowed = {"stars", "compatibility", "comments", "issues"}
        for key, value in fields.items():
            if key in allowed:
                setattr(self, key, value)
        self.updated_at = datetime.now(timezone.utc)

    def lock(self) -> None:
        self.is_locked = True

    def to_trust_data_point(self) -> TrustDataPoint:
        from ..score.score_manager import TrustDataPoint
        return TrustDataPoint(
            agent_id=self.rated_agent_id,
            date_id=self.date_id,
            peer_rating=self,
            task_completed=True,
            is_noshow=False,
            hallucination_confirmed=IssueEnum.HALLUCINATION in self.issues,
        )
