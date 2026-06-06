"""
S4: 랭킹 시스템 — Trust Score
Guide: 시나리오 4 (4-1)

동적 자격증명: 실행마다 신규 UUID (principal 에이전트 누적 방지)
Setup  Principal A·B + 신규 Agent B(BetaBot-{RUN_ID}) 생성

4-1    GET /v1/agents/{B_ID}    → trust_score=null, tier_badge=new_agent, date_count=0
         Ground truth: date_count < 5 → new_agent 배지·trust_score null

Skip (API 미구현):
  4-2  Trust Score 재계산       — trust_data_points 테이블 DB 직접 확인
  4-3  New Agent 배지 전환      — agent_profiles.tier_badge DB 직접 확인
  4-4  가중치 검증              — test_engine/functional/test_req_0401.py 에서 검증
"""
from __future__ import annotations
import sys, os
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

_RUN_ID = uuid4().hex[:6]

from helpers import (
    api_get, api_post,
    check_status, check_field,
    run_suite, _fail,
    make_jwt,
)

# 실행마다 신규 UUID → principal 에이전트 누적 방지
JWT_A = make_jwt(str(uuid4()), f"a-{_RUN_ID}@test.local")
JWT_B = make_jwt(str(uuid4()), f"b-{_RUN_ID}@test.local")

SUITE_ID = "S4-TRUST-SCORE"


def setup(state: dict) -> bool:
    """Principal A·B 멱등 생성 + 신규 Agent B(BetaBot) 생성."""
    for jwt, name in [
        (JWT_A, "Test User"),
        (JWT_B, "User B"),
    ]:
        r = api_post("/v1/principals", jwt, {"name": name})
        if r.status_code != 200:
            print(f"  ERROR setup: principal [{r.status_code}]: {r.text[:200]}")
            return False

    r = api_post("/v1/agents", JWT_B, {
        "display_name": f"BetaBot-{_RUN_ID}",
        "visibility": "PUBLIC",
        "capability_tags": ["coding", "design"],
    })
    if r.status_code != 200:
        print(f"  ERROR setup: Agent B [{r.status_code}]: {r.text[:200]}")
        return False
    state["agent_b_id"] = r.json()["data"]["agent_id"]
    print(f"  SETUP Agent B: {state['agent_b_id']}")
    return True


def test_4_1_new_agent_trust_null(state: dict) -> bool:
    """
    GET /v1/agents/{B_ID} → trust_score=null, tier_badge=new_agent, date_count=0
    Ground truth: date_count < 5 → tier_badge='new_agent', trust_score=null
    """
    agent_b_id = state.get("agent_b_id")
    if not agent_b_id:
        return _fail("4-1 SKIP (no agent_b_id)")

    resp = api_get(f"/v1/agents/{agent_b_id}", JWT_A)
    ok = check_status("4-1 get agent profile", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_field("4-1 trust_score=null",   data, "trust_score", None)
    ok &= check_field("4-1 tier_badge=new_agent", data, "tier_badge", "new_agent")
    ok &= check_field("4-1 date_count=0",        data, "date_count", 0)
    return ok


# ── 4-2 ~ 4-4: API 미구현 — 스킵 ──────────────────────────────────────────

def test_4_2_skip(state: dict) -> bool:
    print("  SKIP  4-2 Trust Score 재계산 — trust_data_points DB 직접 확인 필요 (API 미구현)")
    return True


def test_4_3_skip(state: dict) -> bool:
    print("  SKIP  4-3 배지 전환 — agent_profiles DB 직접 확인 필요 (API 미구현)")
    return True


def test_4_4_skip(state: dict) -> bool:
    print("  SKIP  4-4 가중치 검증 — test_engine/functional/test_req_0401.py 에서 검증")
    return True


def main() -> int:
    state: dict = {}
    if not setup(state):
        print(f"[{SUITE_ID}] SETUP FAILED\n")
        return 1

    tests = [
        ("4-1 new agent trust=null", test_4_1_new_agent_trust_null),
        ("4-2 trust recalc",         test_4_2_skip),
        ("4-3 badge transition",     test_4_3_skip),
        ("4-4 weight validation",    test_4_4_skip),
    ]
    _, f = run_suite(SUITE_ID, tests, state)
    return f


if __name__ == "__main__":
    print(f"\n=== {SUITE_ID} ===")
    sys.exit(0 if main() == 0 else 1)
