"""
UC-0402 — Relationship Tier Upgrade After Successful Dates
Goal: Agents complete dates → conditions met → tier auto-upgraded → notification sent
Actor: Agent A, Agent B, ScoreManager, Backend (notification — stubbed)
Pre-condition: Agents A and B have an existing relationship (STRANGER)
SRS Source: model_requirements.md §ScoreManager §TierEnum, BACKEND_INTERFACE.md §3-11
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.mock_data import make_score_manager
from models.enums import TierEnum
from uuid import uuid4

UC_ID = "UC-0402"


def _stub_send_notification(agent_id, event, tier):
    """Stub: Backend NotificationService sends upgrade notification."""
    print(f"  [Stub] Notification → agent={agent_id} event={event} tier={tier}")
    return True


def test_full_upgrade_path():
    """
    Step 1: Agents start at STRANGER.
    Step 2: Complete 1 date → ACQUAINTANCE.
    Step 3: Complete 3 total dates → COLLEAGUE.
    Step 4: Complete 10 total dates + avg_rating >= 4.0 → TRUSTED_PARTNER.
    Step 5: Notification sent at each upgrade (stubbed).
    """
    print(f"\n--- {UC_ID}: Happy Path — Full Upgrade Path ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    notifications = []

    # Step 1: Initial state
    tier = sm.getRelationship(a, b)
    if tier != TierEnum.STRANGER:
        print(f"  FAIL  Step 1: Expected STRANGER, got {tier}")
        return False
    print("  PASS  Step 1: Initial tier = STRANGER")

    # Step 2: 1 date → ACQUAINTANCE
    sm.recordSuccessfulDate(a, b, rating=4.5)
    new_tier = sm.checkUpgrade(a, b)
    if new_tier != TierEnum.ACQUAINTANCE:
        print(f"  FAIL  Step 2: Expected ACQUAINTANCE, got {new_tier}")
        return False
    notifications.append(_stub_send_notification(a, "tier_upgrade", new_tier))
    print(f"  PASS  Step 2: Upgraded → ACQUAINTANCE")

    # Step 3: 3 total dates → COLLEAGUE
    sm.recordSuccessfulDate(a, b, rating=4.5)
    sm.recordSuccessfulDate(a, b, rating=4.5)
    new_tier = sm.checkUpgrade(a, b)
    if new_tier != TierEnum.COLLEAGUE:
        print(f"  FAIL  Step 3: Expected COLLEAGUE, got {new_tier}")
        return False
    notifications.append(_stub_send_notification(a, "tier_upgrade", new_tier))
    print(f"  PASS  Step 3: Upgraded → COLLEAGUE")

    # Step 4: 10 total dates + avg_rating >= 4.0 → TRUSTED_PARTNER
    for _ in range(7):
        sm.recordSuccessfulDate(a, b, rating=4.5)
    new_tier = sm.checkUpgrade(a, b)
    if new_tier != TierEnum.TRUSTED_PARTNER:
        print(f"  FAIL  Step 4: Expected TRUSTED_PARTNER, got {new_tier}")
        return False
    notifications.append(_stub_send_notification(a, "tier_upgrade", new_tier))
    print(f"  PASS  Step 4: Upgraded → TRUSTED_PARTNER")

    print(f"  PASS  Step 5: {len(notifications)} notifications sent (stub)")
    return True


def test_upgrade_requires_all_conditions():
    """
    Exception: 10 dates but low rating → no TRUSTED_PARTNER upgrade.
    Step 1: Record 10 dates at rating=2.0 (avg < 4.0).
    Step 2: checkUpgrade → None (conditions not met).
    """
    print(f"\n--- {UC_ID}: Exception — Low Rating Blocks Upgrade ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    for _ in range(10):
        sm.recordSuccessfulDate(a, b, rating=2.0)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    sm.checkUpgrade(a, b)  # → COLLEAGUE
    result = sm.checkUpgrade(a, b)  # should NOT upgrade
    if result is not None:
        print(f"  FAIL  Low rating should block TRUSTED_PARTNER: got {result}")
        return False
    print("  PASS  Low avg_rating blocks TRUSTED_PARTNER upgrade")
    return True


def test_freeze_blocks_upgrade_mid_path():
    """
    Exception: Trust score drops during upgrade path → freeze.
    Step 1: 1 date → ready for ACQUAINTANCE.
    Step 2: Freeze applied.
    Step 3: checkUpgrade → None.
    Step 4: Unfreeze → upgrade succeeds.
    """
    print(f"\n--- {UC_ID}: Exception — Freeze Mid-Path ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()

    sm.recordSuccessfulDate(a, b, rating=4.5)
    sm.freeze(a, b)

    # Step 3: Frozen → no upgrade
    result = sm.checkUpgrade(a, b)
    if result is not None:
        print(f"  FAIL  Step 3: Freeze should block upgrade, got {result}")
        return False
    print("  PASS  Step 3: Frozen → no upgrade")

    # Step 4: Unfreeze → upgrade proceeds
    sm.unfreeze(a, b)
    result = sm.checkUpgrade(a, b)
    if result != TierEnum.ACQUAINTANCE:
        print(f"  FAIL  Step 4: After unfreeze expected ACQUAINTANCE, got {result}")
        return False
    print("  PASS  Step 4: Unfrozen → ACQUAINTANCE upgrade")
    return True


def test_one_step_per_call():
    """
    Boundary: checkUpgrade advances only one tier per call (REQ-0406).
    """
    print(f"\n--- {UC_ID}: Boundary — One Step Per Call ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    for _ in range(10):
        sm.recordSuccessfulDate(a, b, rating=5.0)

    result = sm.checkUpgrade(a, b)  # STRANGER → ACQUAINTANCE
    if result != TierEnum.ACQUAINTANCE:
        print(f"  FAIL  First call should → ACQUAINTANCE, got {result}")
        return False
    print("  PASS  10 dates, first checkUpgrade → only ACQUAINTANCE")

    result2 = sm.checkUpgrade(a, b)  # ACQUAINTANCE → COLLEAGUE
    if result2 != TierEnum.COLLEAGUE:
        print(f"  FAIL  Second call should → COLLEAGUE, got {result2}")
        return False
    print("  PASS  Second checkUpgrade → COLLEAGUE (one step)")
    return True


def test_avg_rating_rolling_average():
    """
    Boundary: avg_rating is rolling average of all dates.
    Mix of high and low ratings; verify threshold boundary.
    """
    print(f"\n--- {UC_ID}: Boundary — Rolling Average Rating ---")
    sm = make_score_manager()
    a, b = uuid4(), uuid4()
    # 10 dates: 9 at 5.0, 1 at 3.0 → avg = (9*5+3)/10 = 48/10 = 4.8 >= 4.0
    for i in range(10):
        r = 5.0 if i < 9 else 3.0
        sm.recordSuccessfulDate(a, b, rating=r)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    sm.checkUpgrade(a, b)  # → COLLEAGUE
    result = sm.checkUpgrade(a, b)  # → TRUSTED_PARTNER (avg=4.8 >= 4.0)
    if result != TierEnum.TRUSTED_PARTNER:
        print(f"  FAIL  avg=4.8 should allow TRUSTED_PARTNER, got {result}")
        return False
    print("  PASS  Rolling avg 4.8 satisfies >= 4.0 threshold")
    return True


def main():
    tests = [
        ("full_path", test_full_upgrade_path),
        ("low_rating_blocks", test_upgrade_requires_all_conditions),
        ("freeze_mid_path", test_freeze_blocks_upgrade_mid_path),
        ("one_step", test_one_step_per_call),
        ("rolling_avg", test_avg_rating_rolling_average),
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
    print(f"\n=== {UC_ID}: Relationship Tier Upgrade ===")
    sys.exit(0 if main() == 0 else 1)
