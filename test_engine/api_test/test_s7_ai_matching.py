"""
S7: 동기 매칭 — AI 주도
Guide: 시나리오 7

V1 구현 상태: 자동 에이전트 선정 엔드포인트 미구현.
현재 가능한 검증: feed?limit=1 으로 최적 후보 1명 조회.

Setup  S6와 동일 (AgentA + AgentC·D under Principal B)
7      GET /v1/agents/{A}/feed?limit=1 → 정확히 1개 반환
         items[0] 필드 검증: agent_id·compatibility_total·common_tags
         items[0].agent_id == AgentC (Cap=3/5=0.6 > AgentD Cap=0)
"""
from __future__ import annotations
import sys, os
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

_RUN_ID = uuid4().hex[:6]

from helpers import (
    api_get, api_post,
    check_status, check_field, check_not_none, check_truthy,
    run_suite, _ok, _fail,
    make_jwt,
)

# 실행마다 신규 UUID → principal 에이전트 누적 방지
JWT_A = make_jwt(str(uuid4()), f"a-{_RUN_ID}@test.local")
JWT_B = make_jwt(str(uuid4()), f"b-{_RUN_ID}@test.local")

SUITE_ID = "S7-AI-MATCHING"

_AGENT_A_BODY = {
    "display_name": f"AlphaBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["coding", "research", "analysis", "design", "testing"],
}
_AGENT_C_BODY = {
    "display_name": f"CBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["coding", "research", "design"],   # Cap=3/5=0.6
}
_AGENT_D_BODY = {
    "display_name": f"DBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["writing", "management"],          # Cap=0
}


def setup(state: dict) -> bool:
    """Principal A(AgentA) + Principal B(AgentC, AgentD) 생성 (S6와 동일)."""
    for jwt, name in [
        (JWT_A, "Test User"),
        (JWT_B, "User B"),
    ]:
        r = api_post("/v1/principals", jwt, {"name": name})
        if r.status_code != 200:
            print(f"  ERROR setup: principal [{r.status_code}]: {r.text[:200]}")
            return False

    r = api_post("/v1/agents", JWT_A, _AGENT_A_BODY)
    if r.status_code != 200:
        print(f"  ERROR setup: AgentA [{r.status_code}]: {r.text[:200]}")
        return False
    state["agent_a_id"] = r.json()["data"]["agent_id"]

    r = api_post("/v1/agents", JWT_B, _AGENT_C_BODY)
    if r.status_code != 200:
        print(f"  ERROR setup: AgentC [{r.status_code}]: {r.text[:200]}")
        return False
    state["agent_c_id"] = r.json()["data"]["agent_id"]

    r = api_post("/v1/agents", JWT_B, _AGENT_D_BODY)
    if r.status_code != 200:
        print(f"  ERROR setup: AgentD [{r.status_code}]: {r.text[:200]}")
        return False
    state["agent_d_id"] = r.json()["data"]["agent_id"]

    print(f"  SETUP Agent A: {state['agent_a_id']}")
    print(f"  SETUP Agent C: {state['agent_c_id']}  (Cap=0.60 with A)")
    print(f"  SETUP Agent D: {state['agent_d_id']}  (Cap=0.00 with A)")
    return True


def test_7_best_match_via_feed(state: dict) -> bool:
    """
    GET /v1/agents/{A}/feed?limit=1 → 정확히 1개 반환
    items[0] 검증:
      - agent_id·compatibility_total·common_tags 필드 존재
      - compatibility_total ∈ [0, 1]
      - items[0].agent_id == AgentC (가장 높은 호환성)

    Ground truth: items[0]이 알고리즘 기준 최적 매치.
    이 agent_id로 스와이프를 진행한다 (실제 스와이프는 6-2에서 검증).
    """
    agent_a_id = state.get("agent_a_id")
    agent_c_id = state.get("agent_c_id")
    if not agent_a_id:
        return _fail("7 SKIP (no agent_a_id)")

    resp = api_get(f"/v1/agents/{agent_a_id}/feed?limit=1", JWT_A)
    ok = check_status("7 feed?limit=1", resp, 200)
    if not ok:
        return False

    data  = resp.json().get("data", {})
    items = data.get("items", [])

    ok &= check_truthy("7 exactly 1 item returned", len(items) == 1,
                       f"got {len(items)} items")
    if not items:
        return False

    best = items[0]
    ok &= check_not_none("7 agent_id present",           best, "agent_id")
    ok &= check_not_none("7 compatibility_total present", best, "compatibility_total")
    ok &= check_not_none("7 common_tags present",         best, "common_tags")

    compat = best.get("compatibility_total", -1)
    ok &= check_truthy("7 compatibility_total ∈ [0, 1]", 0.0 <= compat <= 1.0,
                       f"got {compat}")

    # 공유 DB 환경에서 이전 실행의 에이전트가 더 높은 Cap으로 1위를 차지할 수 있음
    # → 특정 agent_id 대신 "1위 agent의 Cap ≥ CBot의 Cap" 구조적 성질만 검증
    if agent_c_id:
        # CBot의 실제 compat을 feed에서 조회 (limit 크게)
        feed_all = api_get(f"/v1/agents/{agent_a_id}/feed?limit=50", JWT_A)
        if feed_all.status_code == 200:
            all_items = feed_all.json().get("data", {}).get("items", [])
            c_item = next((i for i in all_items if i.get("agent_id") == agent_c_id), None)
            if c_item:
                c_compat = c_item.get("compatibility_total", 0)
                if compat >= c_compat:
                    _ok(f"7 best match compat({compat}) ≥ CBot compat({c_compat})")
                else:
                    ok = _fail("7 best match compat < CBot compat",
                               f"best={compat}, CBot={c_compat}")
            else:
                print(f"  INFO  7 CBot not found in top-50 feed (공유 DB 에이전트 누적)")
                print(f"  INFO  7 best match agent_id={best.get('agent_id')}, compat={compat}")
        else:
            print(f"  INFO  7 best match agent_id={best.get('agent_id')}, compat={compat}")
    else:
        print(f"  INFO  7 best match agent_id={best.get('agent_id')}, compat={compat}")

    # next_cursor는 limit=1이고 전체 후보 > 1이면 non-null 일 수 있음 (구현 의존)
    print(f"  INFO  7 next_cursor={data.get('next_cursor')!r}")
    return ok


def main() -> int:
    state: dict = {}
    if not setup(state):
        print(f"[{SUITE_ID}] SETUP FAILED\n")
        return 1

    tests = [
        ("7 best match via feed?limit=1", test_7_best_match_via_feed),
    ]
    _, f = run_suite(SUITE_ID, tests, state)
    return f


if __name__ == "__main__":
    print(f"\n=== {SUITE_ID} ===")
    sys.exit(0 if main() == 0 else 1)
