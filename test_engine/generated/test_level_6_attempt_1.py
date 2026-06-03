# TEST GENERATION EXPERIMENT
# Level: 6  Attempt: 1  Result: (evaluated after run)
# Target REQ: REQ-0505 + REQ-0506 + REQ-0507 — Noshow/Hallucination Penalties + Clamping
# Prompt info: REQ text only (no setup, no expected values, no case types)
# FAILURE MODE RISK: Swapping 0.20/0.15 penalty values; wrong formula direction; missing clamp

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.score.score_manager import ScoreManager, TrustDataPoint
from models.rating.rating import Rating
from uuid import uuid4


def _make_good_dp(agent_id, stars=5):
    r = Rating(date_id=uuid4(), rater_principal_id=uuid4(),
               rated_agent_id=agent_id, stars=stars, compatibility=stars/5.0)
    return TrustDataPoint(agent_id=agent_id, date_id=uuid4(), peer_rating=r, task_completed=True)


def test_noshow_penalty():
    # 5 good points (stars=5, task=True), then 1 noshow (no peer_rating, task=False)
    # After 6 total: peer_vals=[1,1,1,1,1] peer_avg=1.0, task_rate=5/6
    # raw = 0.50*1.0 + 0.30*(5/6) = 0.50 + 0.25 = 0.75
    # noshow penalty = 1*0.20/6 = 0.0333
    # expected composite = 0.75 - 0.0333 = 0.7167
    sm = ScoreManager()
    agent_id = uuid4()
    for _ in range(5):
        sm.addTrustDataPoint(agent_id, _make_good_dp(agent_id, stars=5))
    dp_noshow = TrustDataPoint(
        agent_id=agent_id, date_id=uuid4(),
        task_completed=False, is_noshow=True
    )
    sm.addTrustDataPoint(agent_id, dp_noshow)
    trust = sm.getTrust(agent_id)
    expected = 0.50 * 1.0 + 0.30 * (5/6) - (1 * 0.20) / 6
    if trust is not None and abs(trust - expected) < 0.001:
        print("PASS test_noshow_penalty")
    else:
        print(f"FAIL test_noshow_penalty: expected={expected:.4f}, got={trust}")


def test_hallucination_penalty():
    # 4 good points (stars=5, task=True), 1 hallucination (stars=5, task=True, halluc=True)
    # peer_avg=1.0, task_rate=1.0 → raw=0.50+0.30=0.80
    # halluc penalty = 1*0.15/5 = 0.03
    # expected = 0.80 - 0.03 = 0.77
    sm = ScoreManager()
    agent_id = uuid4()
    for _ in range(4):
        sm.addTrustDataPoint(agent_id, _make_good_dp(agent_id, stars=5))
    r = Rating(date_id=uuid4(), rater_principal_id=uuid4(),
               rated_agent_id=agent_id, stars=5, compatibility=1.0)
    dp_halluc = TrustDataPoint(
        agent_id=agent_id, date_id=uuid4(),
        peer_rating=r, task_completed=True, hallucination_confirmed=True
    )
    sm.addTrustDataPoint(agent_id, dp_halluc)
    trust = sm.getTrust(agent_id)
    expected = 0.50 * 1.0 + 0.30 * 1.0 - (1 * 0.15) / 5
    if trust is not None and abs(trust - expected) < 0.001:
        print("PASS test_hallucination_penalty")
    else:
        print(f"FAIL test_hallucination_penalty: expected={expected:.4f}, got={trust}")


def test_composite_never_below_zero():
    # Many noshows and hallucinations → composite clamped at 0.0
    sm = ScoreManager()
    agent_id = uuid4()
    for _ in range(5):
        dp = TrustDataPoint(
            agent_id=agent_id, date_id=uuid4(),
            task_completed=False, is_noshow=True, hallucination_confirmed=True
        )
        sm.addTrustDataPoint(agent_id, dp)
    trust = sm.getTrust(agent_id)
    if trust is not None and trust >= 0.0:
        print(f"PASS test_composite_never_below_zero (trust={trust:.4f})")
    else:
        print(f"FAIL test_composite_never_below_zero: trust={trust}")


test_noshow_penalty()
test_hallucination_penalty()
test_composite_never_below_zero()
