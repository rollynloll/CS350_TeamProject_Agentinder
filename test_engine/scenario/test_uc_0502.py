"""
UC-0502 — Trust Score Submission and Recalculation
Goal: Principal submits post-date rating → Trust Score recalculated → Feed updated
Actor: Principal, ScoreManager, Backend (feed refresh — stubbed)
Pre-condition: Date completed; Principal has rating to submit; Agent has < 5 data points
SRS Source: model_requirements.md §ScoreManager §TrustScore, BACKEND_INTERFACE.md §3-9, §3-10
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_score_manager, make_trust_data_point
from models.principal.principal import Principal
from models.principal.principal_profile import PrincipalProfile
from models.agent.agent_service import AgentService
from models.rating.rating import Rating
from models.enums import PlanEnum, IssueEnum
from uuid import uuid4

UC_ID = "UC-0502"


def _make_principal(sm):
    return Principal(
        principal_id=uuid4(),
        profile=PrincipalProfile(email="p@test.com", name="P", plan=PlanEnum.FREE),
        agent_service=AgentService(),
        score_manager=sm,
    )


def _make_rating(rated_agent_id, stars=4, issues=None):
    return Rating(
        date_id=uuid4(),
        rater_principal_id=uuid4(),
        rated_agent_id=rated_agent_id,
        stars=stars,
        compatibility=stars / 5.0,
        comments="",
        issues=issues or [],
    )


def _stub_feed_refresh(agent_id):
    """Stub: Backend invalidates feed cache for agent."""
    print(f"  [Stub] Feed refreshed for agent {agent_id}")


def test_rating_activates_trust():
    """
    Step 1: Agent B has 4 existing data points → trust = None.
    Step 2: Principal submits 5th rating.
    Step 3: Trust becomes non-None (recalculated).
    Step 4: Feed refresh triggered (stub).
    """
    print(f"\n--- {UC_ID}: Happy Path — Trust Activated on 5th Rating ---")
    sm = make_score_manager()
    principal = _make_principal(sm)
    agent_b_id = uuid4()

    # Step 1: 4 existing points
    for _ in range(4):
        sm.addTrustDataPoint(agent_b_id, make_trust_data_point(agent_b_id, stars=4))
    if sm.getTrust(agent_b_id) is not None:
        print("  FAIL  Step 1: Trust should be None with 4 points")
        return False
    print("  PASS  Step 1: Trust = None with 4 data points")

    # Step 2: Submit 5th rating
    rating = _make_rating(agent_b_id, stars=5)
    principal.submitRating(date_id=rating.date_id, rating=rating)

    # Step 3: Trust computed
    trust = sm.getTrust(agent_b_id)
    if trust is None:
        print("  FAIL  Step 3: Trust still None after 5th rating")
        return False
    print(f"  PASS  Step 3: Trust = {trust:.4f} (activated)")

    # Step 4: Feed refresh (stub)
    _stub_feed_refresh(agent_b_id)
    print("  PASS  Step 4: Feed refresh triggered (stub)")
    return True


def test_trust_reflects_rating_value():
    """
    Step 1: Submit 5 ratings with stars=5 (all perfect).
    Step 2: Trust score = 0.80 (0.50*1.0 + 0.30*1.0, V1).
    """
    print(f"\n--- {UC_ID}: Trust Value Correctness ---")
    sm = make_score_manager()
    principal = _make_principal(sm)
    agent_id = uuid4()

    for _ in range(5):
        rating = _make_rating(agent_id, stars=5)
        principal.submitRating(date_id=rating.date_id, rating=rating)

    trust = sm.getTrust(agent_id)
    if trust is None or abs(trust - 0.80) > 0.001:
        print(f"  FAIL  Step 2: Expected trust=0.80, got {trust}")
        return False
    print(f"  PASS  Step 2: Trust = {trust:.4f} = 0.80 (correct)")
    return True


def test_hallucination_flag_penalizes_trust():
    """
    Exception: Rating with HALLUCINATION issue reduces trust score.
    Step 1: 5 clean ratings establish baseline.
    Step 2: 6th rating with HALLUCINATION flag submitted.
    Step 3: Trust decreases.
    """
    print(f"\n--- {UC_ID}: Exception — Hallucination Flag Penalizes Trust ---")
    sm = make_score_manager()
    principal = _make_principal(sm)
    agent_id = uuid4()

    for _ in range(5):
        rating = _make_rating(agent_id, stars=5)
        principal.submitRating(date_id=rating.date_id, rating=rating)
    baseline = sm.getTrust(agent_id)

    # Hallucination report
    rating_h = _make_rating(agent_id, stars=5, issues=[IssueEnum.HALLUCINATION])
    principal.submitRating(date_id=rating_h.date_id, rating=rating_h)
    after = sm.getTrust(agent_id)

    if after >= baseline:
        print(f"  FAIL  HALLUCINATION should reduce trust: {baseline:.4f} → {after:.4f}")
        return False
    print(f"  PASS  HALLUCINATION penalty: {baseline:.4f} → {after:.4f}")
    return True


def test_low_stars_reduces_trust():
    """
    Boundary: Low peer_rating reduces composite score.
    Step 1: Mix of 5-star and 1-star ratings.
    Step 2: Trust = 0.50*avg + 0.30*1.0 (all completed).
    """
    print(f"\n--- {UC_ID}: Boundary — Low Stars Reduce Trust ---")
    sm = make_score_manager()
    principal = _make_principal(sm)
    agent_id = uuid4()

    # 3x5★ + 2x1★
    stars_list = [5, 5, 5, 1, 1]
    for s in stars_list:
        rating = _make_rating(agent_id, stars=s)
        principal.submitRating(date_id=rating.date_id, rating=rating)

    trust = sm.getTrust(agent_id)
    # peer_avg = (1+1+1+0.2+0.2)/5 = 3.4/5 = 0.68
    peer_avg = sum(s/5.0 for s in stars_list) / len(stars_list)
    expected = 0.50 * peer_avg + 0.30 * 1.0
    if trust is None or abs(trust - expected) > 0.001:
        print(f"  FAIL  Expected trust={expected:.4f}, got {trust}")
        return False
    print(f"  PASS  Mixed stars: trust={trust:.4f} = {expected:.4f}")
    return True


def test_feed_reflects_updated_trust():
    """
    Step 1: Agent B has low trust → compatibility score uses low trust.
    Step 2: After new rating improves trust → compatibility score increases.
    """
    print(f"\n--- {UC_ID}: Feed Compatibility Updated After Trust Change ---")
    sm = make_score_manager()
    from shared.mock_data import make_profile
    agent_a_id = uuid4()
    agent_b_id = uuid4()

    profile_a = make_profile(capability_tags=["coding"], date_count=10)
    profile_a.agent_id = agent_a_id
    profile_b = make_profile(capability_tags=["coding"], date_count=10)
    profile_b.agent_id = agent_b_id

    # Add 5 low-star points to B
    for _ in range(5):
        sm.addTrustDataPoint(agent_b_id, make_trust_data_point(agent_b_id, stars=1))
    score_before = sm.getCompatibility(profile_a, profile_b).total

    # Add high-star points to improve B's trust
    for _ in range(5):
        sm.addTrustDataPoint(agent_b_id, make_trust_data_point(agent_b_id, stars=5))
    score_after = sm.getCompatibility(profile_a, profile_b).total

    if score_after <= score_before:
        print(f"  FAIL  Improved trust should increase compat: {score_before:.4f} → {score_after:.4f}")
        return False
    print(f"  PASS  Trust improvement raises compat: {score_before:.4f} → {score_after:.4f}")
    _stub_feed_refresh(agent_b_id)
    return True


def main():
    tests = [
        ("activates_on_5th", test_rating_activates_trust),
        ("correct_value", test_trust_reflects_rating_value),
        ("hallucination_penalty", test_hallucination_flag_penalizes_trust),
        ("low_stars", test_low_stars_reduces_trust),
        ("feed_reflects", test_feed_reflects_updated_trust),
    ]
    p = f = 0
    for name, fn in tests:
        try:
            ok = fn()
            if ok: p += 1
            else: f += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            f += 1
    print(f"\n[{UC_ID}] {p} passed, {f} failed\n")
    return f


if __name__ == "__main__":
    print(f"\n=== {UC_ID}: Trust Score Submission & Recalculation ===")
    sys.exit(0 if main() == 0 else 1)
