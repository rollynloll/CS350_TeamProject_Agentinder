from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from ..enums import TierEnum

if TYPE_CHECKING:
    from ..agent.agent_profile import AgentProfile
    from ..rating.rating import Rating


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

@dataclass
class TrustDataPoint:
    agent_id: UUID
    date_id: UUID
    peer_rating: Optional[Rating] = None
    task_completed: bool = True
    is_noshow: bool = False
    hallucination_confirmed: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TrustBreakdown:
    composite: float
    peer_ratings_avg: float
    task_completion_rate: float
    other: float
    data_point_count: int


@dataclass
class CompatibilityScore:
    agent_a_id: UUID
    agent_b_id: UUID
    total: float
    capability_score: float
    style_score: float
    trust_score: float
    common_tags: List[str]
    complementary_tags: List[str]
    style_diff: Dict[str, float]
    trust_level: TierEnum
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ScoreBreakdown:
    common_tags: List[str]
    complementary_tags: List[str]
    style_diff: Dict[str, float]
    trust_level: TierEnum
    capability_score: float
    style_score: float
    trust_score: float
    total: float


@dataclass
class RelationshipRecord:
    agent_a_id: UUID
    agent_b_id: UUID
    tier: TierEnum = TierEnum.STRANGER
    successful_dates: int = 0
    avg_rating: float = 0.0
    is_frozen: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# ScoreManager
# ---------------------------------------------------------------------------

_NEW_AGENT_THRESHOLD = 5
_MIN_TRUST_POINTS = 5
_NOSHOW_PENALTY = 0.20
_HALLUCINATION_PENALTY = 0.15

_W_PEER = 0.50
_W_TASK = 0.30
_W_OTHER = 0.20

_W_CAP = 0.50
_W_STYLE = 0.20
_W_TRUST = 0.30

# ACQUAINTANCE+ agents only visible above this trust score
RESTRICTED_VISIBILITY_THRESHOLD = 0.5


class ScoreManager:
    def __init__(self) -> None:
        # agent_id → list of data points
        self._trust_data: Dict[UUID, List[TrustDataPoint]] = {}
        # agent_id → cached composite score (None = new agent)
        self._trust_cache: Dict[UUID, Optional[float]] = {}
        # (min_id, max_id) → RelationshipRecord
        self._relationships: Dict[Tuple[UUID, UUID], RelationshipRecord] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key(self, a: UUID, b: UUID) -> Tuple[UUID, UUID]:
        """Always store as (smaller_uuid, larger_uuid) to avoid duplicates."""
        return (a, b) if str(a) < str(b) else (b, a)

    def _get_or_create_rel(self, a: UUID, b: UUID) -> RelationshipRecord:
        key = self._key(a, b)
        if key not in self._relationships:
            self._relationships[key] = RelationshipRecord(agent_a_id=key[0], agent_b_id=key[1])
        return self._relationships[key]

    # ------------------------------------------------------------------
    # Trust Scorer
    # ------------------------------------------------------------------

    def getTrust(self, agent_id: UUID) -> Optional[float]:
        """Returns composite trust score, or None if fewer than 5 data points."""
        return self._trust_cache.get(agent_id)

    def getTrustBreakdown(self, agent_id: UUID) -> TrustBreakdown:
        points = self._trust_data.get(agent_id, [])
        count = len(points)
        if count < _MIN_TRUST_POINTS:
            return TrustBreakdown(
                composite=0.0,
                peer_ratings_avg=0.0,
                task_completion_rate=0.0,
                other=0.0,
                data_point_count=count,
            )

        peer_vals = [
            p.peer_rating.stars / 5.0
            for p in points
            if p.peer_rating is not None
        ]
        peer_avg = sum(peer_vals) / len(peer_vals) if peer_vals else 0.0
        task_rate = sum(1 for p in points if p.task_completed) / count

        composite = _W_PEER * peer_avg + _W_TASK * task_rate

        noshow_count = sum(1 for p in points if p.is_noshow)
        halluc_count = sum(1 for p in points if p.hallucination_confirmed)
        composite -= noshow_count * _NOSHOW_PENALTY / count
        composite -= halluc_count * _HALLUCINATION_PENALTY / count
        composite = max(0.0, min(1.0, composite))

        return TrustBreakdown(
            composite=composite,
            peer_ratings_avg=peer_avg,
            task_completion_rate=task_rate,
            other=0.0,
            data_point_count=count,
        )

    def addTrustDataPoint(self, agent_id: UUID, data: TrustDataPoint) -> None:
        self._trust_data.setdefault(agent_id, []).append(data)
        self._recalculate_trust(agent_id)

    def _recalculate_trust(self, agent_id: UUID) -> None:
        breakdown = self.getTrustBreakdown(agent_id)
        if breakdown.data_point_count < _MIN_TRUST_POINTS:
            self._trust_cache[agent_id] = None
        else:
            self._trust_cache[agent_id] = breakdown.composite

    # ------------------------------------------------------------------
    # Compatibility Scorer
    # ------------------------------------------------------------------

    def getCompatibility(
        self, profile_a: AgentProfile, profile_b: AgentProfile
    ) -> CompatibilityScore:
        # Capability: Jaccard similarity (V1)
        tags_a = set(profile_a.capability_tags)
        tags_b = set(profile_b.capability_tags)
        union = tags_a | tags_b
        intersection = tags_a & tags_b
        cap_score = len(intersection) / len(union) if union else 0.0

        common_tags = sorted(intersection)
        complementary_tags = sorted(union - intersection)

        # Style: inverse Euclidean distance over slider vectors
        sv_a = profile_a.style_vector
        sv_b = profile_b.style_vector
        all_keys = set(sv_a) | set(sv_b)
        style_diff: Dict[str, float] = {
            k: abs(sv_a.get(k, 0.0) - sv_b.get(k, 0.0)) for k in all_keys
        }
        dist = math.sqrt(sum(v ** 2 for v in style_diff.values()))
        style_score = 1.0 / (1.0 + dist)

        # Trust of the target agent (b)
        is_new_b = profile_b.date_count < _NEW_AGENT_THRESHOLD
        trust_b = self.getTrust(profile_b.agent_id) or 0.0

        if is_new_b:
            # Exclude trust; re-normalize Cap and Style to sum to 1.0
            cap_weight = _W_CAP / (_W_CAP + _W_STYLE)
            style_weight = _W_STYLE / (_W_CAP + _W_STYLE)
            total = cap_weight * cap_score + style_weight * style_score
            trust_score = 0.0
        else:
            total = _W_CAP * cap_score + _W_STYLE * style_score + _W_TRUST * trust_b
            trust_score = trust_b

        total = max(0.0, min(1.0, total))

        rel = self._get_or_create_rel(profile_a.agent_id, profile_b.agent_id)

        return CompatibilityScore(
            agent_a_id=profile_a.agent_id,
            agent_b_id=profile_b.agent_id,
            total=total,
            capability_score=cap_score,
            style_score=style_score,
            trust_score=trust_score,
            common_tags=common_tags,
            complementary_tags=complementary_tags,
            style_diff=style_diff,
            trust_level=rel.tier,
        )

    def explain(
        self, profile_a: AgentProfile, profile_b: AgentProfile
    ) -> ScoreBreakdown:
        score = self.getCompatibility(profile_a, profile_b)
        return ScoreBreakdown(
            common_tags=score.common_tags,
            complementary_tags=score.complementary_tags,
            style_diff=score.style_diff,
            trust_level=score.trust_level,
            capability_score=score.capability_score,
            style_score=score.style_score,
            trust_score=score.trust_score,
            total=score.total,
        )

    # ------------------------------------------------------------------
    # Relationship Manager
    # ------------------------------------------------------------------

    def getRelationship(self, agent_a_id: UUID, agent_b_id: UUID) -> TierEnum:
        key = self._key(agent_a_id, agent_b_id)
        rel = self._relationships.get(key)
        return rel.tier if rel else TierEnum.STRANGER

    def checkUpgrade(
        self, agent_a_id: UUID, agent_b_id: UUID
    ) -> Optional[TierEnum]:
        """Checks and applies tier upgrade. Returns new tier if upgraded, else None."""
        rel = self._get_or_create_rel(agent_a_id, agent_b_id)
        if rel.is_frozen:
            return None

        current = rel.tier
        new_tier = current

        if current == TierEnum.STRANGER and rel.successful_dates >= 1:
            new_tier = TierEnum.ACQUAINTANCE
        elif current == TierEnum.ACQUAINTANCE and rel.successful_dates >= 3:
            new_tier = TierEnum.COLLEAGUE
        elif (
            current == TierEnum.COLLEAGUE
            and rel.successful_dates >= 10
            and rel.avg_rating >= 4.0
        ):
            new_tier = TierEnum.TRUSTED_PARTNER

        if new_tier != current:
            rel.tier = new_tier
            rel.updated_at = datetime.now(timezone.utc)
            return new_tier
        return None

    def recordSuccessfulDate(
        self, agent_a_id: UUID, agent_b_id: UUID, rating: float
    ) -> None:
        """Called after a successful date to update relationship counters."""
        rel = self._get_or_create_rel(agent_a_id, agent_b_id)
        n = rel.successful_dates
        rel.avg_rating = (rel.avg_rating * n + rating) / (n + 1)
        rel.successful_dates += 1
        rel.updated_at = datetime.now(timezone.utc)

    def freeze(self, agent_a_id: UUID, agent_b_id: UUID) -> None:
        rel = self._get_or_create_rel(agent_a_id, agent_b_id)
        rel.is_frozen = True

    def unfreeze(self, agent_a_id: UUID, agent_b_id: UUID) -> None:
        rel = self._get_or_create_rel(agent_a_id, agent_b_id)
        rel.is_frozen = False
