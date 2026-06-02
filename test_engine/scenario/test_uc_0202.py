"""
UC-0202 — Match Creation Flow
Goal: Agent A swipes RIGHT on Agent B → mutual match detected → icebreaker stub generated
Actor: Agent (automated), Backend (stubbed)
Pre-condition: Agents A and B exist; Agent B has RIGHT-swiped Agent A (stored in Backend stub)
SRS Source: PROJECT_README.md §3-5, BACKEND_INTERFACE.md §3-5
Note: Full match deduplication and icebreaker generation live in Team A's backend.
      This scenario tests the Model layer's swipe() interface contract and match return.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_profile, make_score_manager
from models.agent.agent import Agent
from models.agent.agent_personality import AgentPersonality
from models.enums import SwipeEnum
from models.types import Match
from uuid import uuid4

UC_ID = "UC-0202"


def _make_agent(capability_tags=None, date_count=0):
    agent_id = uuid4()
    profile = make_profile(
        capability_tags=capability_tags or ["coding"],
        date_count=date_count,
    )
    profile.agent_id = agent_id
    personality = AgentPersonality(
        surface={"bio": "test", "style_sliders": {}},
        deep={}, aspiration={}
    )
    return Agent(
        agent_id=agent_id,
        principal_id=uuid4(),
        profile=profile,
        personality=personality,
    )


def _stub_icebreakers(match_id, agent_a, agent_b):
    """Stub: Backend IcebreakerGenerator produces 3 questions."""
    # SRS REQ-0204: 3 icebreakers per match
    tags_a = set(agent_a.getProfile().capability_tags)
    tags_b = set(agent_b.getProfile().capability_tags)
    common = tags_a & tags_b
    return [
        f"How do you approach {list(common)[0] if common else 'collaboration'}?",
        "What's your preferred working style?",
        "What goals are you hoping to accomplish together?",
    ]


def test_right_swipe_returns_match():
    """
    Step 1: Agent A swipes RIGHT on Agent B.
    Step 2: Backend detects mutual RIGHT (stub: always mutual).
    Step 3: Match object returned with correct agent IDs.
    """
    print(f"\n--- {UC_ID}: Happy Path — Swipe + Match ---")
    a = _make_agent(capability_tags=["coding", "research"])
    b = _make_agent(capability_tags=["coding", "writing"])

    # Step 1: Agent A swipes RIGHT
    match = a.swipe(target_id=b.agent_id, direction=SwipeEnum.RIGHT)

    # Step 2: Verify Match returned (mutual detected by stub model)
    if match is None:
        print("  FAIL  Step 2: Expected Match, got None")
        return False
    print("  PASS  Step 2: Match created")

    # Step 3: Verify agent IDs
    if match.agent_a_id != a.agent_id or match.agent_b_id != b.agent_id:
        print(f"  FAIL  Step 3: Wrong agent IDs in match")
        return False
    print("  PASS  Step 3: Match has correct agent IDs")

    return True


def test_left_swipe_returns_none():
    """
    Step 1: Agent A swipes LEFT on Agent B.
    Step 2: No match created — returns None.
    """
    print(f"\n--- {UC_ID}: Exception — Left Swipe ---")
    a = _make_agent()
    b = _make_agent()

    # Step 1: LEFT swipe
    match = a.swipe(target_id=b.agent_id, direction=SwipeEnum.LEFT)

    # Step 2: No match
    if match is not None:
        print("  FAIL  LEFT swipe should return None")
        return False
    print("  PASS  LEFT swipe → None (no match)")
    return True


def test_icebreaker_generation():
    """
    Step 1: Match created.
    Step 2: Backend generates 3 icebreakers (stubbed here).
    Step 3: Exactly 3 icebreakers returned.
    """
    print(f"\n--- {UC_ID}: Icebreaker Generation ---")
    a = _make_agent(capability_tags=["coding"])
    b = _make_agent(capability_tags=["coding"])

    # Step 1: Create match
    match = a.swipe(target_id=b.agent_id, direction=SwipeEnum.RIGHT)
    assert match is not None

    # Step 2: Generate icebreakers (Backend stub)
    icebreakers = _stub_icebreakers(match.match_id, a, b)

    # Step 3: Verify exactly 3 icebreakers (REQ-0204)
    if len(icebreakers) != 3:
        print(f"  FAIL  Expected 3 icebreakers, got {len(icebreakers)}")
        return False
    print(f"  PASS  3 icebreakers generated: {icebreakers}")
    return True


def test_superlike_creates_match():
    """
    Step 1: Agent A sends SUPER LIKE (UP swipe).
    Step 2: Match still returned (UP is also a match-eligible direction).
    """
    print(f"\n--- {UC_ID}: Exception — Super Like ---")
    a = _make_agent()
    b = _make_agent()
    match = a.swipe(target_id=b.agent_id, direction=SwipeEnum.UP)
    if match is None:
        print("  FAIL  Super like (UP) should return Match")
        return False
    print("  PASS  Super like creates match")
    return True


def test_match_has_uuid():
    """
    Step 1: Swipe creates match.
    Step 2: Match has a valid match_id UUID.
    """
    print(f"\n--- {UC_ID}: Match ID Validity ---")
    a = _make_agent()
    b = _make_agent()
    match = a.swipe(target_id=b.agent_id, direction=SwipeEnum.RIGHT)
    if match is None or match.match_id is None:
        print("  FAIL  Match missing match_id")
        return False
    print(f"  PASS  Match UUID: {match.match_id}")
    return True


def main():
    results = []
    tests = [
        ("right_swipe_match", test_right_swipe_returns_match),
        ("left_swipe_none", test_left_swipe_returns_none),
        ("icebreaker_generation", test_icebreaker_generation),
        ("superlike_match", test_superlike_creates_match),
        ("match_uuid", test_match_has_uuid),
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
    print(f"\n=== {UC_ID}: Match Creation Flow ===")
    sys.exit(0 if main() == 0 else 1)
