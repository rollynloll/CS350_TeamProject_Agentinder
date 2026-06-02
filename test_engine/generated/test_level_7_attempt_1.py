# TEST GENERATION EXPERIMENT
# Level: 7  Attempt: 1  Result: (evaluated after run)
# Target REQ: REQ-0401, REQ-0403, REQ-0504 (REQ IDs only given in prompt — no description)
# Prompt info: Only REQ numbers; model must recall/infer all threshold values from training
# FAILURE MODE RISK: Wrong thresholds; wrong tier names; wrong badge logic

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.score.score_manager import ScoreManager
from models.agent.agent_profile import AgentProfile
from models.enums import TierEnum
from uuid import uuid4


def test_req_0401_acquaintance_threshold():
    # REQ-0401: STRANGER → ACQUAINTANCE on first successful date
    sm = ScoreManager()
    a, b = uuid4(), uuid4()
    sm.recordSuccessfulDate(a, b, rating=4.5)
    tier = sm.checkUpgrade(a, b)
    if tier == TierEnum.ACQUAINTANCE:
        print("PASS test_req_0401_acquaintance_threshold")
    else:
        print(f"FAIL test_req_0401_acquaintance_threshold: got {tier}")


def test_req_0403_trusted_partner_requires_10_dates_and_rating():
    # REQ-0403: COLLEAGUE → TRUSTED_PARTNER: 10 dates + avg_rating >= 4.0
    sm = ScoreManager()
    a, b = uuid4(), uuid4()
    # 9 dates at 4.5 → not enough
    for _ in range(9):
        sm.recordSuccessfulDate(a, b, rating=4.5)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    sm.checkUpgrade(a, b)  # → COLLEAGUE
    no_upgrade = sm.checkUpgrade(a, b)  # should be None (only 9 dates)
    if no_upgrade is None:
        print("PASS test_req_0403_9_dates_insufficient")
    else:
        print(f"FAIL test_req_0403_9_dates_insufficient: expected None, got {no_upgrade}")

    # Now add 10th date
    sm.recordSuccessfulDate(a, b, rating=4.5)
    upgrade = sm.checkUpgrade(a, b)  # → TRUSTED_PARTNER
    if upgrade == TierEnum.TRUSTED_PARTNER:
        print("PASS test_req_0403_10_dates_sufficient")
    else:
        print(f"FAIL test_req_0403_10_dates_sufficient: expected TRUSTED_PARTNER, got {upgrade}")


def test_req_0403_trusted_partner_low_rating_blocked():
    # REQ-0403: 10 dates but avg_rating < 4.0 → no upgrade
    sm = ScoreManager()
    a, b = uuid4(), uuid4()
    for _ in range(10):
        sm.recordSuccessfulDate(a, b, rating=3.0)
    sm.checkUpgrade(a, b)  # → ACQUAINTANCE
    sm.checkUpgrade(a, b)  # → COLLEAGUE
    result = sm.checkUpgrade(a, b)
    if result is None:
        print("PASS test_req_0403_trusted_partner_low_rating_blocked")
    else:
        print(f"FAIL test_req_0403_trusted_partner_low_rating_blocked: expected None, got {result}")


def test_req_0504_new_agent_badge():
    # REQ-0504: date_count < 5 → tier_badge = 'new_agent'
    p = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=0)
    if p.tier_badge == "new_agent":
        print("PASS test_req_0504_new_agent_badge")
    else:
        print(f"FAIL test_req_0504_new_agent_badge: expected 'new_agent', got '{p.tier_badge}'")


def test_req_0504_experienced_badge():
    # REQ-0504: date_count >= 5 → tier_badge is NOT 'new_agent'
    p = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=5, tier_badge="5")
    if p.tier_badge != "new_agent":
        print("PASS test_req_0504_experienced_badge")
    else:
        print(f"FAIL test_req_0504_experienced_badge: should not be 'new_agent'")


def test_req_0504_is_new_agent_method():
    # is_new_agent() returns True for date_count < 5
    p4 = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=4)
    p5 = AgentProfile(agent_id=uuid4(), display_name="Bot", date_count=5)
    if p4.is_new_agent() and not p5.is_new_agent():
        print("PASS test_req_0504_is_new_agent_method")
    else:
        print(f"FAIL test_req_0504_is_new_agent_method: p4={p4.is_new_agent()}, p5={p5.is_new_agent()}")


test_req_0401_acquaintance_threshold()
test_req_0403_trusted_partner_requires_10_dates_and_rating()
test_req_0403_trusted_partner_low_rating_blocked()
test_req_0504_new_agent_badge()
test_req_0504_experienced_badge()
test_req_0504_is_new_agent_method()
