"""
S6: 동기 매칭 — 유저 주도
Guide: 시나리오 6 (6-1, 6-2)

Setup  Principal A: AgentA (coding,research,analysis,design,testing)
       Principal B: AgentC (coding,research,design)  ← A와 3개 공통 → 높은 Cap
                    AgentD (writing,management)       ← A와 0개 공통 → Cap=0

6-1    GET /v1/agents/{A}/feed → items 내림차순 정렬 검증 (AgentC > AgentD)
         호환성 공식 (new_agent):
           A vs C: Cap=|{coding,research,design}|/|{coding,research,analysis,design,testing}|=3/5=0.6
           A vs D: Cap=0/7=0
           → C가 D보다 먼저 출력되어야 함

6-2    A→C 스와이프 right → C→A 스와이프 right → 매치 생성 → 승인 → 데이트 제안
       (시나리오 3-2 ~ 3-5와 동일 흐름)
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

SUITE_ID = "S6-SYNC-MATCHING"

_AGENT_A_BODY = {
    "display_name": f"AlphaBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    # A vs C → Cap=3/5=0.60, A vs D → Cap=0/7=0
    "capability_tags": ["coding", "research", "analysis", "design", "testing"],
}
_AGENT_C_BODY = {
    "display_name": f"CBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["coding", "research", "design"],
}
_AGENT_D_BODY = {
    "display_name": f"DBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["writing", "management"],
}


def setup(state: dict) -> bool:
    """Principal A(AgentA) + Principal B(AgentC, AgentD) 생성."""
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
    print(f"  SETUP Agent C: {state['agent_c_id']}")
    print(f"  SETUP Agent D: {state['agent_d_id']}")
    return True


# ── 6-1 ──────────────────────────────────────────────────────────────────────

def test_6_1_feed_sorted(state: dict) -> bool:
    """
    GET /v1/agents/{A}/feed → 호환성 내림차순 정렬 검증

    예상:
      CBot (Cap=3/5=0.6) > DBot (Cap=0)
    검증:
      1. items 내림차순 (items[i].compat >= items[i+1].compat)
      2. CBot이 DBot보다 먼저 등장
      3. 각 항목의 compatibility_total ∈ [0, 1]
    """
    agent_a_id = state.get("agent_a_id")
    agent_c_id = state.get("agent_c_id")
    agent_d_id = state.get("agent_d_id")
    if not all([agent_a_id, agent_c_id, agent_d_id]):
        return _fail("6-1 SKIP (setup state 누락)")

    # limit=50: DB에 이전 실행 에이전트가 누적되므로 충분한 범위를 조회
    resp = api_get(f"/v1/agents/{agent_a_id}/feed?limit=50", JWT_A)
    ok = check_status("6-1 feed", resp, 200)
    if not ok:
        return False

    items = resp.json().get("data", {}).get("items", [])
    ok &= check_truthy("6-1 items not empty", len(items) > 0)
    if not items:
        return False

    # 내림차순 정렬 확인
    for i in range(len(items) - 1):
        if items[i]["compatibility_total"] < items[i + 1]["compatibility_total"]:
            ok = _fail(
                "6-1 정렬 오류",
                f"items[{i}]={items[i]['compatibility_total']} < items[{i+1}]={items[i+1]['compatibility_total']}"
            )
            break
    else:
        _ok("6-1 items 내림차순 정렬 확인")

    # compatibility_total 범위 확인
    for item in items:
        compat = item.get("compatibility_total", -1)
        if not (0.0 <= compat <= 1.0):
            ok = _fail("6-1 compatibility_total 범위", f"got {compat}")
            break
    else:
        _ok("6-1 compatibility_total ∈ [0, 1]")

    # CBot · DBot 위치 확인
    # 공유 DB 환경에서 이전 실행 에이전트가 섞여 limit 내에 없을 수 있음
    # → 두 개 모두 발견되면 CBot ≥ DBot Cap 이 보장되는지만 검증
    ids = [i.get("agent_id") for i in items]
    c_pos = ids.index(agent_c_id) if agent_c_id in ids else -1
    d_pos = ids.index(agent_d_id) if agent_d_id in ids else -1

    if c_pos == -1:
        ok = _fail("6-1 CBot not in feed (limit=50 내 미검출)")
    elif d_pos == -1:
        # DB 내 다른 에이전트가 많아 DBot(Cap=0)이 50위 밖으로 밀릴 수 있음
        _ok("6-1 CBot in feed")
        print("  INFO  6-1 DBot not in top-50 (공유 DB 에이전트 누적으로 인한 한계)")
    elif c_pos < d_pos:
        _ok(f"6-1 CBot(idx={c_pos}, cap={items[c_pos].get('compatibility_total')}) "
            f"> DBot(idx={d_pos}, cap={items[d_pos].get('compatibility_total')})")
    else:
        ok = _fail(
            "6-1 정렬 순서 오류",
            f"CBot(idx={c_pos}) should be before DBot(idx={d_pos})"
        )

    return ok


# ── 6-2 ──────────────────────────────────────────────────────────────────────

def test_6_2_swipe_match_date(state: dict) -> bool:
    """
    A→C right, C→A right → 매치 생성 → 승인 → 데이트 제안
    시나리오 3-2 ~ 3-5와 동일 흐름
    """
    agent_a_id = state.get("agent_a_id")
    agent_c_id = state.get("agent_c_id")
    if not agent_a_id or not agent_c_id:
        return _fail("6-2 SKIP (setup state 누락)")

    ok = True

    # A → C 스와이프
    r = api_post(f"/v1/agents/{agent_a_id}/swipe", JWT_A,
                 {"target_id": agent_c_id, "direction": "right"})
    ok &= check_status("6-2 swipe A→C", r, 200)
    ok &= check_field("6-2 match=null (단방향)", r.json().get("data", {}), "match", None)

    # C → A 스와이프 (매치 생성)
    r = api_post(f"/v1/agents/{agent_c_id}/swipe", JWT_B,
                 {"target_id": agent_a_id, "direction": "right"})
    ok &= check_status("6-2 swipe C→A (mutual)", r, 200)
    match = r.json().get("data", {}).get("match")
    if match and match.get("match_id"):
        _ok("6-2 match 생성")
        state["match_id"] = match["match_id"]
    else:
        ok = _fail("6-2 match not created")
        return ok

    # 매치 승인
    r = api_post(f"/v1/matches/{state['match_id']}/approve", JWT_A)
    ok &= check_status("6-2 approve match", r, 200)
    ok &= check_field("6-2 status=approved", r.json().get("data", {}), "status", "approved")

    # 데이트 제안
    r = api_post(f"/v1/matches/{state['match_id']}/dates", JWT_A, {
        "type": "coffee_chat",
        "scheduled_at": "2026-06-10T14:00:00Z",
    })
    ok &= check_status("6-2 propose date", r, 200)
    ok &= check_not_none("6-2 date_id", r.json().get("data", {}), "date_id")

    return ok


def main() -> int:
    state: dict = {}
    if not setup(state):
        print(f"[{SUITE_ID}] SETUP FAILED\n")
        return 1

    tests = [
        ("6-1 feed sorted",        test_6_1_feed_sorted),
        ("6-2 swipe→match→date",   test_6_2_swipe_match_date),
    ]
    _, f = run_suite(SUITE_ID, tests, state)
    return f


if __name__ == "__main__":
    print(f"\n=== {SUITE_ID} ===")
    sys.exit(0 if main() == 0 else 1)
