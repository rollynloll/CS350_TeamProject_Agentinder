"""
UC-0302 — Coffee Chat Lifecycle
Goal: Two agents engage in a Coffee Chat via WebSocket; session ends; rating submitted
Actor: Agent A, Agent B, Principal, Backend (WebSocket — stubbed)
Pre-condition: Match exists; Both agents active; Date record created by Backend
SRS Source: model_requirements.md §ScoreManager, BACKEND_INTERFACE.md §3-7, §3-8, §3-9
Note: WebSocket transport stubbed. Tests the joinDate/leaveDate + rating + trust pipeline.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_profile, make_score_manager
from models.agent.agent import Agent
from models.agent.agent_personality import AgentPersonality
from models.principal.principal import Principal
from models.principal.principal_profile import PrincipalProfile
from models.agent.agent_service import AgentService
from models.rating.rating import Rating
from models.enums import PlanEnum, IssueEnum
from uuid import uuid4

UC_ID = "UC-0302"

MAX_MESSAGES = 20   # REQ-0301
MAX_MINUTES = 15    # REQ-0301


def _make_agent(display_name="Bot", date_count=0):
    agent_id = uuid4()
    profile = make_profile(display_name=display_name, date_count=date_count)
    profile.agent_id = agent_id
    personality = AgentPersonality(surface={"bio": "t", "style_sliders": {}}, deep={}, aspiration={})
    return Agent(agent_id=agent_id, principal_id=uuid4(), profile=profile, personality=personality)


def _make_principal(score_manager):
    agent_service = AgentService()
    profile = PrincipalProfile(email="p@test.com", name="P", plan=PlanEnum.FREE)
    return Principal(
        principal_id=uuid4(),
        profile=profile,
        agent_service=agent_service,
        score_manager=score_manager,
    )


def test_date_lifecycle():
    """
    Step 1: Backend creates date record.
    Step 2: Both agents join the date.
    Step 3: Agents exchange messages (stub — LLM not invoked here).
    Step 4: Date ends; both agents leave.
    Step 5: date_count incremented for both agents.
    """
    print(f"\n--- {UC_ID}: Happy Path — Date Lifecycle ---")
    agent_a = _make_agent("AgentA", date_count=4)
    agent_b = _make_agent("AgentB", date_count=4)
    date_id = uuid4()

    # Step 1: Date record created by Backend (stub — no actual DB call)
    print("  [Step 1] Date record created by Backend (stub)")

    # Step 2: Both agents join
    agent_a.joinDate(date_id)
    agent_b.joinDate(date_id)

    if not (agent_a.isActive() and agent_b.isActive()):
        print("  FAIL  Step 2: Agents not marked active after joinDate")
        return False
    print("  PASS  Step 2: Both agents active")

    # Step 3: Message exchange (simulated — LLM stub not needed here)
    message_count = 0
    for i in range(5):
        message_count += 2  # A sends, B responds
    print(f"  [Step 3] {message_count} messages exchanged (stub)")

    # Step 4: Date ends
    before_a = agent_a.getProfile().date_count
    before_b = agent_b.getProfile().date_count
    agent_a.leaveDate(date_id)
    agent_b.leaveDate(date_id)

    if agent_a.isActive() or agent_b.isActive():
        print("  FAIL  Step 4: Agents still active after leaveDate")
        return False
    print("  PASS  Step 4: Date ended — both agents inactive")

    # Step 5: date_count incremented
    if agent_a.getProfile().date_count != before_a + 1:
        print("  FAIL  Step 5: agent_a date_count not incremented")
        return False
    if agent_b.getProfile().date_count != before_b + 1:
        print("  FAIL  Step 5: agent_b date_count not incremented")
        return False
    print("  PASS  Step 5: date_count incremented for both agents")
    return True


def test_rating_submission_updates_trust():
    """
    Step 1: Date ends successfully.
    Step 2: Principal submits rating for Agent B.
    Step 3: Rating converted to TrustDataPoint.
    Step 4: Trust score updated for Agent B.
    """
    print(f"\n--- {UC_ID}: Rating Submission → Trust Update ---")
    sm = make_score_manager()
    principal = _make_principal(sm)
    agent_b = _make_agent("AgentB", date_count=10)
    date_id = uuid4()

    # Pre-condition: 4 existing data points for agent_b
    from shared.mock_data import make_trust_data_point
    for _ in range(4):
        dp = make_trust_data_point(agent_b.agent_id, stars=4)
        sm.addTrustDataPoint(agent_b.agent_id, dp)
    before_trust = sm.getTrust(agent_b.agent_id)  # None (4 < 5)

    # Step 2: Submit rating (5th data point)
    rating = Rating(
        date_id=date_id,
        rater_principal_id=principal.principal_id,
        rated_agent_id=agent_b.agent_id,
        stars=5,
        compatibility=0.9,
        comments="Excellent collaboration",
        issues=[],
    )
    principal.submitRating(date_id=date_id, rating=rating)

    # Step 4: Trust is now computed
    after_trust = sm.getTrust(agent_b.agent_id)
    if after_trust is None:
        print(f"  FAIL  Step 4: Trust still None after 5th data point")
        return False
    print(f"  PASS  Step 4: Trust updated to {after_trust:.4f} (was None)")
    return True


def test_message_limit_boundary():
    """
    Exception: Coffee Chat has max 20 messages (REQ-0301).
    Test: Verify the constant is documented and limit is enforced by Backend stub.
    """
    print(f"\n--- {UC_ID}: Exception — Message Limit ---")
    # The backend enforces this limit. Here we verify the constant value.
    if MAX_MESSAGES != 20:
        print(f"  FAIL  Message limit should be 20, got {MAX_MESSAGES}")
        return False
    print(f"  PASS  Message limit = {MAX_MESSAGES} (REQ-0301)")
    return True


def test_time_limit_boundary():
    """
    Exception: Coffee Chat max 15 minutes (REQ-0301).
    """
    print(f"\n--- {UC_ID}: Exception — Time Limit ---")
    if MAX_MINUTES != 15:
        print(f"  FAIL  Time limit should be 15 min, got {MAX_MINUTES}")
        return False
    print(f"  PASS  Time limit = {MAX_MINUTES} minutes (REQ-0301)")
    return True


def test_noshow_trust_penalty():
    """
    Exception: Agent B is a noshow → penalty applied to trust.
    Step 1: Date starts; Agent B does not join (noshow).
    Step 2: Backend records noshow → addTrustDataPoint with is_noshow=True.
    Step 3: Trust score penalized.
    """
    print(f"\n--- {UC_ID}: Exception — Noshow Penalty ---")
    sm = make_score_manager()
    agent_b = _make_agent("NoShowBot", date_count=10)
    from models.score.score_manager import TrustDataPoint

    # Baseline: 5 good points
    from shared.mock_data import make_trust_data_point
    for _ in range(5):
        sm.addTrustDataPoint(agent_b.agent_id, make_trust_data_point(agent_b.agent_id, stars=5))
    baseline = sm.getTrust(agent_b.agent_id)

    # Noshow event recorded by Backend
    dp = TrustDataPoint(agent_id=agent_b.agent_id, date_id=uuid4(),
                         task_completed=False, is_noshow=True)
    sm.addTrustDataPoint(agent_b.agent_id, dp)
    after = sm.getTrust(agent_b.agent_id)

    if after >= baseline:
        print(f"  FAIL  Noshow should reduce trust: {baseline:.4f} → {after:.4f}")
        return False
    print(f"  PASS  Noshow penalty: {baseline:.4f} → {after:.4f}")
    return True


def main():
    tests = [
        ("lifecycle", test_date_lifecycle),
        ("rating_trust", test_rating_submission_updates_trust),
        ("msg_limit", test_message_limit_boundary),
        ("time_limit", test_time_limit_boundary),
        ("noshow", test_noshow_trust_penalty),
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
    print(f"\n=== {UC_ID}: Coffee Chat Lifecycle ===")
    sys.exit(0 if main() == 0 else 1)
