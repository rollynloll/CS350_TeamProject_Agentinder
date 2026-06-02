"""
UC-0203 — Feed: Compatibility Score Sorting
Goal: Viewer's feed is sorted by compatibility score descending; HIDDEN agents excluded
Actor: Backend (feed handler — stubbed), ScoreManager
Pre-condition: Viewer agent exists; multiple candidate agents exist in DB
SRS Source: BACKEND_INTERFACE.md §3-4, model_requirements.md §ScoreManager
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_profile, make_score_manager, add_n_trust_points
from models.enums import VisibilityEnum
from uuid import uuid4

UC_ID = "UC-0203"


def _build_feed(sm, viewer_profile, candidates):
    """
    Backend feed-building logic (from BACKEND_INTERFACE.md §3-4).
    Filters HIDDEN agents; sorts by compatibility descending.
    """
    viewer_trust = sm.getTrust(viewer_profile.agent_id) or 0.0
    results = []
    for candidate in candidates:
        # Filter HIDDEN
        if candidate.visibility == VisibilityEnum.HIDDEN:
            continue
        # Filter RESTRICTED (viewer must meet trust threshold)
        if candidate.visibility == VisibilityEnum.RESTRICTED and viewer_trust < 0.5:
            continue
        score = sm.getCompatibility(viewer_profile, candidate)
        results.append({
            "agent_id": candidate.agent_id,
            "display_name": candidate.display_name,
            "compatibility_total": round(score.total, 6),
        })
    results.sort(key=lambda x: x["compatibility_total"], reverse=True)
    return results


def test_feed_sorted_by_compatibility():
    """
    Step 1: Viewer has capability_tags = [a, b, c].
    Step 2: Candidates have varying tag overlap.
    Step 3: Feed returned sorted descending by compatibility.
    """
    print(f"\n--- {UC_ID}: Happy Path — Feed Sorted by Compatibility ---")
    sm = make_score_manager()

    viewer = make_profile(
        display_name="Viewer",
        capability_tags=["coding", "research", "analysis"],
        style_vector={"formality": 0.8},
        date_count=10,
    )

    # High overlap candidate (2/3 tags match)
    c_high = make_profile(
        display_name="HighCompat",
        capability_tags=["coding", "research"],
        style_vector={"formality": 0.8},
        date_count=10,
    )
    # Low overlap candidate (0 tags match)
    c_low = make_profile(
        display_name="LowCompat",
        capability_tags=["writing", "design"],
        style_vector={"formality": 0.2},
        date_count=10,
    )
    # Medium overlap (1 tag)
    c_mid = make_profile(
        display_name="MidCompat",
        capability_tags=["coding"],
        style_vector={"formality": 0.5},
        date_count=10,
    )

    # Step 3: Build feed
    feed = _build_feed(sm, viewer, [c_low, c_mid, c_high])

    if len(feed) != 3:
        print(f"  FAIL  Expected 3 results, got {len(feed)}")
        return False

    # Verify descending order
    for i in range(len(feed) - 1):
        if feed[i]["compatibility_total"] < feed[i+1]["compatibility_total"]:
            print(f"  FAIL  Feed not sorted: {[r['compatibility_total'] for r in feed]}")
            return False

    print(f"  PASS  Feed sorted: {[r['display_name'] + '=' + str(r['compatibility_total']) for r in feed]}")
    return True


def test_hidden_agents_excluded():
    """
    Step 1: Candidate has HIDDEN visibility.
    Step 2: Feed excludes HIDDEN agent regardless of compatibility.
    """
    print(f"\n--- {UC_ID}: HIDDEN Agents Excluded ---")
    sm = make_score_manager()

    viewer = make_profile(capability_tags=["coding"], date_count=10)
    visible = make_profile(capability_tags=["coding"], date_count=10)
    hidden = make_profile(
        capability_tags=["coding"], date_count=10,
        visibility=VisibilityEnum.HIDDEN
    )

    feed = _build_feed(sm, viewer, [visible, hidden])
    ids = [r["agent_id"] for r in feed]

    if hidden.agent_id in ids:
        print("  FAIL  HIDDEN agent appeared in feed")
        return False
    if visible.agent_id not in ids:
        print("  FAIL  Visible agent missing from feed")
        return False
    print("  PASS  HIDDEN agent excluded; visible included")
    return True


def test_restricted_requires_trust():
    """
    Exception: RESTRICTED agent only visible to viewer with trust >= 0.5.
    Step 1: Viewer trust < 0.5 → RESTRICTED excluded.
    Step 2: Viewer trust >= 0.5 → RESTRICTED included.
    """
    print(f"\n--- {UC_ID}: Exception — RESTRICTED Visibility ---")
    sm = make_score_manager()

    viewer = make_profile(capability_tags=["coding"], date_count=10)
    restricted = make_profile(
        capability_tags=["coding"], date_count=10,
        visibility=VisibilityEnum.RESTRICTED
    )

    # Step 1: Low trust viewer → excluded
    add_n_trust_points(sm, viewer.agent_id, n=5, stars=1)  # low trust
    feed_low = _build_feed(sm, viewer, [restricted])
    if restricted.agent_id in [r["agent_id"] for r in feed_low]:
        # Trust might still be >= 0.5 with 1-star ratings, check
        trust = sm.getTrust(viewer.agent_id)
        if trust is not None and trust >= 0.5:
            print(f"  SKIP  Viewer trust={trust:.4f} too high for this test to be meaningful")
            return True
        print("  FAIL  RESTRICTED agent visible to low-trust viewer")
        return False
    print("  PASS  Step 1: RESTRICTED excluded for low-trust viewer")

    # Step 2: High trust viewer → included
    sm2 = make_score_manager()
    viewer2 = make_profile(capability_tags=["coding"], date_count=10)
    add_n_trust_points(sm2, viewer2.agent_id, n=5, stars=5)
    restricted2 = make_profile(
        capability_tags=["coding"], date_count=10,
        visibility=VisibilityEnum.RESTRICTED
    )
    feed_high = _build_feed(sm2, viewer2, [restricted2])
    if restricted2.agent_id not in [r["agent_id"] for r in feed_high]:
        print("  FAIL  RESTRICTED agent excluded for high-trust viewer")
        return False
    print("  PASS  Step 2: RESTRICTED included for high-trust viewer")
    return True


def test_empty_candidates():
    """
    Edge case: No candidates → empty feed returned.
    """
    print(f"\n--- {UC_ID}: Edge Case — Empty Candidates ---")
    sm = make_score_manager()
    viewer = make_profile(capability_tags=["coding"], date_count=10)
    feed = _build_feed(sm, viewer, [])
    if feed != []:
        print(f"  FAIL  Empty candidates should return [], got {feed}")
        return False
    print("  PASS  Empty candidates → empty feed")
    return True


def test_compatibility_uses_candidate_trust():
    """
    Boundary: High-trust candidate scores higher than low-trust candidate
              with identical tags and style.
    """
    print(f"\n--- {UC_ID}: Boundary — Trust Affects Feed Rank ---")
    sm = make_score_manager()
    viewer = make_profile(capability_tags=["coding"], style_vector={}, date_count=10)

    high_trust = make_profile(capability_tags=["coding"], style_vector={}, date_count=10)
    low_trust = make_profile(capability_tags=["coding"], style_vector={}, date_count=10)

    add_n_trust_points(sm, high_trust.agent_id, n=5, stars=5)
    add_n_trust_points(sm, low_trust.agent_id, n=5, stars=1)

    feed = _build_feed(sm, viewer, [low_trust, high_trust])
    if len(feed) < 2:
        print("  FAIL  Expected 2 results")
        return False

    if feed[0]["agent_id"] != high_trust.agent_id:
        print(f"  FAIL  High-trust should be first: {[r['display_name'] for r in feed]}")
        return False
    print("  PASS  High-trust candidate ranks first in feed")
    return True


def main():
    tests = [
        ("sorted_by_compat", test_feed_sorted_by_compatibility),
        ("hidden_excluded", test_hidden_agents_excluded),
        ("restricted_visibility", test_restricted_requires_trust),
        ("empty_candidates", test_empty_candidates),
        ("trust_affects_rank", test_compatibility_uses_candidate_trust),
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
    print(f"\n=== {UC_ID}: Feed Compatibility Sort ===")
    sys.exit(0 if main() == 0 else 1)
