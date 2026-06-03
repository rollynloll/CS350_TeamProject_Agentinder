"""
REQ-0504 — tier_badge and New Agent Status
Source: model_requirements.md > AgentProfile > tier_badge
Rule: tier_badge = 'new_agent' when date_count < 5; else numeric string
      isNewAgent() returns True when date_count < 5
Code: agent_profile.py lines 36-37, score_manager.py:83
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_profile, assert_equal, assert_true, run_suite
from models.agent.agent_profile import AgentProfile
from models.enums import VisibilityEnum
from uuid import uuid4

REQ_ID = "REQ-0504"


def test_new_agent_badge_below_5():
    """Happy path: date_count < 5 → tier_badge = 'new_agent'."""
    # SRS REQ-0504
    p = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=0)
    return assert_equal("date_count=0 → tier_badge='new_agent'", p.tier_badge, "new_agent")


def test_is_new_agent_true_below_5():
    """Happy path: is_new_agent() returns True when date_count < 5."""
    for dc in [0, 1, 2, 3, 4]:
        p = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=dc)
        if not p.is_new_agent():
            print(f"  FAIL  date_count={dc} → is_new_agent() returned False")
            return False
    print("  PASS  is_new_agent() = True for date_count in 0..4")
    return True


def test_is_new_agent_false_at_5():
    """Boundary: date_count=5 → is_new_agent() returns False."""
    p = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=5)
    return assert_equal("date_count=5 → is_new_agent()=False", p.is_new_agent(), False)


def test_tier_badge_default():
    """Boundary: Default AgentProfile has tier_badge='new_agent'."""
    p = AgentProfile(agent_id=uuid4(), display_name="Bot")
    return assert_equal("Default tier_badge='new_agent'", p.tier_badge, "new_agent")


def test_tier_badge_update():
    """Happy path: tier_badge can be set to numeric string via update()."""
    p = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=5)
    p.update({"tier_badge": "5", "date_count": 5})
    return assert_equal("tier_badge set to '5' via update()", p.tier_badge, "5")


def test_date_count_increases():
    """Boundary: date_count update changes is_new_agent() result."""
    p = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=4)
    before = p.is_new_agent()
    p.update({"date_count": 5})
    after = p.is_new_agent()
    return assert_equal("date_count 4→5 flips is_new_agent() True→False",
                         (before, after), (True, False))


def test_new_agent_threshold_exact():
    """Edge case: Threshold is strictly < 5, not <= 5."""
    p4 = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=4)
    p5 = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=5)
    ok = p4.is_new_agent() and not p5.is_new_agent()
    return assert_equal("Threshold exactly at 5: 4 is new, 5 is not", ok, True)


if __name__ == "__main__":
    print(f"\n=== {REQ_ID}: tier_badge / New Agent Status ===")
    tests = [
        ("badge_below_5", test_new_agent_badge_below_5),
        ("is_new_true_below_5", test_is_new_agent_true_below_5),
        ("is_new_false_at_5", test_is_new_agent_false_at_5),
        ("default_badge", test_tier_badge_default),
        ("badge_update", test_tier_badge_update),
        ("date_count_increase", test_date_count_increases),
        ("threshold_exact", test_new_agent_threshold_exact),
    ]
    p, f = run_suite(REQ_ID, tests)
    sys.exit(0 if f == 0 else 1)
