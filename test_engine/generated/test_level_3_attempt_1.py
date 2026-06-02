# TEST GENERATION EXPERIMENT
# Level: 3  Attempt: 1  Result: (evaluated after run)
# Target REQ: REQ-0206 — New Agent Trust Exclusion + Re-normalization
# Prompt info: REQ text + setup + expected values for all 3 case types given

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.score.score_manager import ScoreManager, TrustDataPoint
from models.agent.agent_profile import AgentProfile
from models.rating.rating import Rating
from uuid import uuid4

_CAP_W_NEW = 5 / 7
_STY_W_NEW = 2 / 7


def _make_profile(tags, style, date_count):
    return AgentProfile(agent_id=uuid4(), display_name="Bot",
                        capability_tags=tags, style_vector=style, date_count=date_count)


def _add_trust(sm, agent_id, n=5, stars=5):
    for _ in range(n):
        r = Rating(date_id=uuid4(), rater_principal_id=uuid4(),
                   rated_agent_id=agent_id, stars=stars, compatibility=stars/5.0)
        dp = TrustDataPoint(agent_id=agent_id, date_id=uuid4(),
                             peer_rating=r, task_completed=True)
        sm.addTrustDataPoint(agent_id, dp)


def test_happy_new_agent():
    # REQ-0206: date_count=0, Cap=1, Style=1 → total=(5/7)*1+(2/7)*1=1.0
    sm = ScoreManager()
    pa = _make_profile(["a","b"], {}, 10)
    pb = _make_profile(["a","b"], {}, 0)
    score = sm.getCompatibility(pa, pb)
    expected = min(1.0, _CAP_W_NEW * 1.0 + _STY_W_NEW * 1.0)
    if abs(score.total - expected) < 0.001:
        print("PASS test_happy_new_agent")
    else:
        print(f"FAIL test_happy_new_agent: expected={expected:.4f}, got={score.total:.4f}")


def test_boundary_date_count():
    # date_count=4 → new agent; date_count=5 → experienced
    sm = ScoreManager()
    pa = _make_profile(["a","b"], {}, 10)

    pb4 = _make_profile(["a","b"], {}, 4)
    score4 = sm.getCompatibility(pa, pb4)
    exp4 = min(1.0, _CAP_W_NEW * 1.0 + _STY_W_NEW * 1.0)

    pb5 = _make_profile(["a","b"], {}, 5)
    score5 = sm.getCompatibility(pa, pb5)
    # no trust data → composite=None → trust_b=0.0
    exp5 = 0.50 * 1.0 + 0.20 * 1.0 + 0.30 * 0.0

    ok4 = abs(score4.total - exp4) < 0.001
    ok5 = abs(score5.total - exp5) < 0.001
    if ok4:
        print("PASS test_boundary_date_count_4")
    else:
        print(f"FAIL test_boundary_date_count_4: expected={exp4:.4f}, got={score4.total:.4f}")
    if ok5:
        print("PASS test_boundary_date_count_5")
    else:
        print(f"FAIL test_boundary_date_count_5: expected={exp5:.4f}, got={score5.total:.4f}")


def test_exception_trust_ignored_for_new_agent():
    # date_count=2 but has trust data → trust still excluded
    sm = ScoreManager()
    pa = _make_profile(["a","b"], {}, 10)
    pb = _make_profile(["a","b"], {}, 2)
    _add_trust(sm, pb.agent_id, n=5, stars=5)  # composite would be 0.80 if used
    score = sm.getCompatibility(pa, pb)
    expected = min(1.0, _CAP_W_NEW * 1.0 + _STY_W_NEW * 1.0)
    if abs(score.total - expected) < 0.001:
        print("PASS test_exception_trust_ignored_for_new_agent")
    else:
        print(f"FAIL test_exception_trust_ignored_for_new_agent: expected={expected:.4f}, got={score.total:.4f}")


test_happy_new_agent()
test_boundary_date_count()
test_exception_trust_ignored_for_new_agent()
