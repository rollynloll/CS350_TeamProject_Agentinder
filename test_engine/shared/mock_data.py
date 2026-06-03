"""Shared mock data and helpers for both functional and scenario test engines."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from uuid import uuid4
from models.agent.agent_profile import AgentProfile
from models.enums import VisibilityEnum, IssueEnum
from models.score.score_manager import TrustDataPoint, ScoreManager


def make_profile(
    capability_tags=None,
    style_vector=None,
    date_count=10,
    display_name="TestAgent",
    visibility=VisibilityEnum.PUBLIC,
) -> AgentProfile:
    return AgentProfile(
        agent_id=uuid4(),
        display_name=display_name,
        capability_tags=capability_tags or [],
        style_vector=style_vector or {},
        date_count=date_count,
        visibility=visibility,
    )


def make_score_manager() -> ScoreManager:
    return ScoreManager()


def make_trust_data_point(agent_id, date_id=None, stars=4, task_completed=True,
                           is_noshow=False, hallucination=False):
    from models.rating.rating import Rating
    from uuid import uuid4 as _uuid4
    date_id = date_id or _uuid4()
    rating = Rating(
        date_id=date_id,
        rater_principal_id=_uuid4(),
        rated_agent_id=agent_id,
        stars=stars,
        compatibility=stars / 5.0,
        comments="",
        issues=[IssueEnum.HALLUCINATION] if hallucination else [],
    )
    return TrustDataPoint(
        agent_id=agent_id,
        date_id=date_id,
        peer_rating=rating,
        task_completed=task_completed,
        is_noshow=is_noshow,
        hallucination_confirmed=hallucination,
    )


def add_n_trust_points(sm: ScoreManager, agent_id, n=5, stars=4, task_completed=True):
    for _ in range(n):
        dp = make_trust_data_point(agent_id, stars=stars, task_completed=task_completed)
        sm.addTrustDataPoint(agent_id, dp)


PRINT_PASS = lambda label: print(f"  PASS  {label}")
PRINT_FAIL = lambda label, got, exp: print(f"  FAIL  {label} — got={got!r}, expected={exp!r}")


def assert_close(label, got, expected, tol=0.001):
    if abs(got - expected) <= tol:
        PRINT_PASS(label)
        return True
    else:
        PRINT_FAIL(label, got, expected)
        return False


def assert_equal(label, got, expected):
    if got == expected:
        PRINT_PASS(label)
        return True
    else:
        PRINT_FAIL(label, got, expected)
        return False


def assert_true(label, condition, detail=""):
    if condition:
        PRINT_PASS(label)
        return True
    else:
        print(f"  FAIL  {label}{' — ' + detail if detail else ''}")
        return False


def run_suite(req_id, tests):
    """Run a list of (label, callable) test pairs; return (passed, failed)."""
    passed = failed = 0
    for label, fn in tests:
        try:
            ok = fn()
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR {label} — {type(e).__name__}: {e}")
            failed += 1
    print(f"\n[{req_id}] {passed} passed, {failed} failed\n")
    return passed, failed
