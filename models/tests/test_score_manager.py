"""Tests for ScoreManager — trust, compatibility, relationship."""
import pytest
from uuid import uuid4

from models.score.score_manager import (
    ScoreManager,
    TrustDataPoint,
    CompatibilityScore,
    ScoreBreakdown,
    TrustBreakdown,
)
from models.enums import TierEnum, VisibilityEnum
from models.agent.agent_profile import AgentProfile
from models.rating.rating import Rating


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_dp(agent_id, stars=4, task_completed=True, is_noshow=False, hallucination=False):
    pid = uuid4()
    r = Rating(
        date_id=uuid4(),
        rater_principal_id=pid,
        rated_agent_id=agent_id,
        stars=stars,
        compatibility=0.8,
    )
    return TrustDataPoint(
        agent_id=agent_id,
        date_id=r.date_id,
        peer_rating=r,
        task_completed=task_completed,
        is_noshow=is_noshow,
        hallucination_confirmed=hallucination,
    )


def _fill_trust(score_mgr, agent_id, n=5, stars=4):
    for _ in range(n):
        score_mgr.addTrustDataPoint(agent_id, _make_dp(agent_id, stars=stars))


def _make_profile(tags, style=None, date_count=10):
    return AgentProfile(
        agent_id=uuid4(),
        display_name="TestBot",
        capability_tags=tags,
        style_vector=style or {"formality": 0.5},
        date_count=date_count,
    )


# ── Trust Scorer ──────────────────────────────────────────────────────────────

class TestTrustScore:
    def test_none_before_five_points(self, score_mgr):
        aid = uuid4()
        assert score_mgr.getTrust(aid) is None

    def test_none_with_four_points(self, score_mgr):
        aid = uuid4()
        _fill_trust(score_mgr, aid, n=4)
        assert score_mgr.getTrust(aid) is None

    def test_not_none_after_five_points(self, score_mgr):
        aid = uuid4()
        _fill_trust(score_mgr, aid, n=5)
        assert score_mgr.getTrust(aid) is not None

    def test_score_between_zero_and_one(self, score_mgr):
        aid = uuid4()
        _fill_trust(score_mgr, aid, n=5)
        trust = score_mgr.getTrust(aid)
        assert 0.0 <= trust <= 1.0

    def test_five_star_higher_than_one_star(self, score_mgr):
        aid_high = uuid4()
        aid_low = uuid4()
        _fill_trust(score_mgr, aid_high, stars=5)
        _fill_trust(score_mgr, aid_low, stars=1)
        assert score_mgr.getTrust(aid_high) > score_mgr.getTrust(aid_low)

    def test_noshow_penalty_reduces_score(self, score_mgr):
        aid_clean = uuid4()
        aid_noshow = uuid4()
        _fill_trust(score_mgr, aid_clean, n=5)
        # 5 clean points then 1 noshow
        _fill_trust(score_mgr, aid_noshow, n=5)
        score_mgr.addTrustDataPoint(aid_noshow, _make_dp(aid_noshow, is_noshow=True))
        assert score_mgr.getTrust(aid_noshow) < score_mgr.getTrust(aid_clean)

    def test_hallucination_penalty_reduces_score(self, score_mgr):
        aid_clean = uuid4()
        aid_halluc = uuid4()
        _fill_trust(score_mgr, aid_clean, n=5)
        _fill_trust(score_mgr, aid_halluc, n=5)
        score_mgr.addTrustDataPoint(aid_halluc, _make_dp(aid_halluc, hallucination=True))
        assert score_mgr.getTrust(aid_halluc) < score_mgr.getTrust(aid_clean)

    def test_score_not_below_zero(self, score_mgr):
        aid = uuid4()
        for _ in range(10):
            score_mgr.addTrustDataPoint(aid, _make_dp(aid, stars=1, is_noshow=True, hallucination=True))
        assert score_mgr.getTrust(aid) >= 0.0

    def test_score_not_above_one(self, score_mgr):
        aid = uuid4()
        _fill_trust(score_mgr, aid, n=10, stars=5)
        assert score_mgr.getTrust(aid) <= 1.0


class TestTrustBreakdown:
    def test_breakdown_under_five_points(self, score_mgr):
        aid = uuid4()
        _fill_trust(score_mgr, aid, n=3)
        bd = score_mgr.getTrustBreakdown(aid)
        assert isinstance(bd, TrustBreakdown)
        assert bd.data_point_count == 3
        assert bd.composite == 0.0

    def test_breakdown_fields(self, score_mgr):
        aid = uuid4()
        _fill_trust(score_mgr, aid, n=5, stars=4)
        bd = score_mgr.getTrustBreakdown(aid)
        assert bd.data_point_count == 5
        assert 0.0 <= bd.peer_ratings_avg <= 1.0
        assert 0.0 <= bd.task_completion_rate <= 1.0
        assert 0.0 <= bd.composite <= 1.0

    def test_formula_weights(self, score_mgr):
        """composite = 0.5*peer_avg + 0.3*task_rate (V1 other=0)."""
        aid = uuid4()
        _fill_trust(score_mgr, aid, n=5, stars=5)  # all 5★, all completed
        bd = score_mgr.getTrustBreakdown(aid)
        expected = 0.50 * 1.0 + 0.30 * 1.0
        assert abs(bd.composite - expected) < 1e-6


# ── Compatibility Scorer ──────────────────────────────────────────────────────

class TestCompatibilityScore:
    def test_returns_compatibility_score(self, score_mgr):
        pa = _make_profile(["coding", "analysis"])
        pb = _make_profile(["coding", "testing"])
        result = score_mgr.getCompatibility(pa, pb)
        assert isinstance(result, CompatibilityScore)

    def test_total_between_zero_and_one(self, score_mgr):
        pa = _make_profile(["coding"])
        pb = _make_profile(["coding"])
        score = score_mgr.getCompatibility(pa, pb)
        assert 0.0 <= score.total <= 1.0

    def test_identical_tags_give_cap_one(self, score_mgr):
        tags = ["coding", "testing"]
        pa = _make_profile(tags)
        pb = _make_profile(tags)
        score = score_mgr.getCompatibility(pa, pb)
        assert score.capability_score == 1.0

    def test_disjoint_tags_give_cap_zero(self, score_mgr):
        pa = _make_profile(["coding"])
        pb = _make_profile(["design"])
        score = score_mgr.getCompatibility(pa, pb)
        assert score.capability_score == 0.0

    def test_common_tags_populated(self, score_mgr):
        pa = _make_profile(["coding", "writing"])
        pb = _make_profile(["coding", "testing"])
        score = score_mgr.getCompatibility(pa, pb)
        assert "coding" in score.common_tags
        assert "writing" not in score.common_tags

    def test_complementary_tags_populated(self, score_mgr):
        pa = _make_profile(["coding", "writing"])
        pb = _make_profile(["coding", "testing"])
        score = score_mgr.getCompatibility(pa, pb)
        assert "writing" in score.complementary_tags
        assert "testing" in score.complementary_tags

    def test_score_asymmetric(self, score_mgr):
        """S(A→B) can differ from S(B→A) due to different trust scores."""
        aid_a = uuid4()
        aid_b = uuid4()
        pa = AgentProfile(
            agent_id=aid_a,
            display_name="A",
            capability_tags=["coding"],
            style_vector={"formality": 0.2},
            date_count=10,
        )
        pb = AgentProfile(
            agent_id=aid_b,
            display_name="B",
            capability_tags=["coding"],
            style_vector={"formality": 0.8},
            date_count=10,
        )
        # Give B a trust score
        for _ in range(5):
            score_mgr.addTrustDataPoint(aid_b, _make_dp(aid_b, stars=5))

        score_ab = score_mgr.getCompatibility(pa, pb)
        score_ba = score_mgr.getCompatibility(pb, pa)
        # B has trust score, A does not → A→B includes trust, B→A uses A's None trust
        assert score_ab.trust_score > score_ba.trust_score

    def test_new_agent_excludes_trust(self, score_mgr):
        """Target agent with date_count < 5 should have trust_score=0 in result."""
        aid_new = uuid4()
        pa = _make_profile(["coding"], date_count=10)
        pb = AgentProfile(
            agent_id=aid_new,
            display_name="NewBot",
            capability_tags=["coding"],
            style_vector={"formality": 0.5},
            date_count=2,  # < 5
        )
        # Even if we add trust data points, new agent should exclude trust component
        _fill_trust(score_mgr, aid_new, n=5, stars=5)
        score = score_mgr.getCompatibility(pa, pb)
        assert score.trust_score == 0.0

    def test_trust_level_is_tier(self, score_mgr):
        pa = _make_profile(["coding"])
        pb = _make_profile(["coding"])
        score = score_mgr.getCompatibility(pa, pb)
        assert isinstance(score.trust_level, TierEnum)

    def test_explain_returns_breakdown(self, score_mgr):
        pa = _make_profile(["coding", "writing"])
        pb = _make_profile(["coding", "testing"])
        bd = score_mgr.explain(pa, pb)
        assert isinstance(bd, ScoreBreakdown)
        assert "coding" in bd.common_tags
        assert bd.total == score_mgr.getCompatibility(pa, pb).total


# ── Relationship Manager ──────────────────────────────────────────────────────

class TestRelationshipManager:
    def test_default_tier_stranger(self, score_mgr):
        a, b = uuid4(), uuid4()
        assert score_mgr.getRelationship(a, b) == TierEnum.STRANGER

    def test_upgrade_to_acquaintance_at_1_date(self, score_mgr):
        a, b = uuid4(), uuid4()
        rel = score_mgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        new_tier = score_mgr.checkUpgrade(a, b)
        assert new_tier == TierEnum.ACQUAINTANCE
        assert score_mgr.getRelationship(a, b) == TierEnum.ACQUAINTANCE

    def test_no_upgrade_before_threshold(self, score_mgr):
        a, b = uuid4(), uuid4()
        # 0 dates → stays STRANGER
        result = score_mgr.checkUpgrade(a, b)
        assert result is None
        assert score_mgr.getRelationship(a, b) == TierEnum.STRANGER

    def test_upgrade_to_colleague_at_3_dates(self, score_mgr):
        a, b = uuid4(), uuid4()
        rel = score_mgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        score_mgr.checkUpgrade(a, b)  # → ACQUAINTANCE
        rel.successful_dates = 3
        new_tier = score_mgr.checkUpgrade(a, b)
        assert new_tier == TierEnum.COLLEAGUE

    def test_upgrade_to_trusted_partner_at_10_dates_with_rating(self, score_mgr):
        a, b = uuid4(), uuid4()
        rel = score_mgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        score_mgr.checkUpgrade(a, b)
        rel.successful_dates = 3
        score_mgr.checkUpgrade(a, b)
        rel.successful_dates = 10
        rel.avg_rating = 4.0
        new_tier = score_mgr.checkUpgrade(a, b)
        assert new_tier == TierEnum.TRUSTED_PARTNER

    def test_no_upgrade_to_trusted_partner_without_rating(self, score_mgr):
        a, b = uuid4(), uuid4()
        rel = score_mgr._get_or_create_rel(a, b)
        # checkUpgrade moves one step at a time:
        # STRANGER(0) → need dates>=1 → ACQUAINTANCE → need dates>=3 → COLLEAGUE
        rel.successful_dates = 3
        score_mgr.checkUpgrade(a, b)  # STRANGER → ACQUAINTANCE (dates >= 1)
        score_mgr.checkUpgrade(a, b)  # ACQUAINTANCE → COLLEAGUE (dates >= 3)
        assert score_mgr.getRelationship(a, b) == TierEnum.COLLEAGUE
        rel.successful_dates = 10
        rel.avg_rating = 3.9  # just below threshold
        result = score_mgr.checkUpgrade(a, b)
        assert result is None
        assert score_mgr.getRelationship(a, b) == TierEnum.COLLEAGUE

    def test_frozen_blocks_upgrade(self, score_mgr):
        a, b = uuid4(), uuid4()
        score_mgr.freeze(a, b)
        rel = score_mgr._get_or_create_rel(a, b)
        rel.successful_dates = 5
        result = score_mgr.checkUpgrade(a, b)
        assert result is None

    def test_unfreeze_allows_upgrade(self, score_mgr):
        a, b = uuid4(), uuid4()
        score_mgr.freeze(a, b)
        score_mgr.unfreeze(a, b)
        rel = score_mgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        result = score_mgr.checkUpgrade(a, b)
        assert result == TierEnum.ACQUAINTANCE

    def test_key_symmetry(self, score_mgr):
        """(a, b) and (b, a) should resolve to the same relationship."""
        a, b = uuid4(), uuid4()
        rel = score_mgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        score_mgr.checkUpgrade(a, b)
        assert score_mgr.getRelationship(b, a) == TierEnum.ACQUAINTANCE

    def test_record_successful_date_updates_avg(self, score_mgr):
        a, b = uuid4(), uuid4()
        score_mgr.recordSuccessfulDate(a, b, rating=4.0)
        score_mgr.recordSuccessfulDate(a, b, rating=2.0)
        rel = score_mgr._get_or_create_rel(a, b)
        assert abs(rel.avg_rating - 3.0) < 1e-6
        assert rel.successful_dates == 2
