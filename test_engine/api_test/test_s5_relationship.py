"""
S5: 관계 단계 업데이트
Guide: 시나리오 5 (5-1 ~ 5-4)

Setup  Full pipeline: A·B 생성 → 상호 스와이프 → 매치 승인
5-1    end_date 1회 (rating_stars=4) → 200 OK
         Ground truth: sm.recordSuccessfulDate → sm.checkUpgrade → ACQUAINTANCE
5-2    end_date 2회 추가 (총 3회)   → 200 OK
         Ground truth: successful_dates=3 → COLLEAGUE
5-3    end_date 7회 추가 (총 10회)  → 200 OK
         Ground truth: successful_dates=10 + avg_rating≥4.0 → TRUSTED_PARTNER
         + GET /v1/agents/{B_ID} → trust_score 변화 여부 소프트 확인

Skip (API 미구현):
  5-1~5-3 relationship 단계(tier) REST 조회 — relationships 테이블 직접 확인
  5-4     Freeze                             — SQL 직접 조작만 가능

Note: end_date 는 WS join 없이도 호출 가능 (날짜 시작 여부 미검증).
      각 데이트 주기: POST /v1/matches/{M}/dates → POST /v1/dates/{D}/end
동적 자격증명: 실행마다 신규 UUID (principal 에이전트 누적 방지)
"""
from __future__ import annotations
import sys, os
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

_RUN_ID = uuid4().hex[:6]

from helpers import (
    api_get, api_post,
    check_status, check_field, check_truthy,
    run_suite, _ok, _fail,
    make_jwt,
)

# 실행마다 신규 UUID → principal 에이전트 누적 방지
JWT_A = make_jwt(str(uuid4()), f"a-{_RUN_ID}@test.local")
JWT_B = make_jwt(str(uuid4()), f"b-{_RUN_ID}@test.local")

SUITE_ID = "S5-RELATIONSHIP"

_AGENT_A_BODY = {
    "display_name": f"AlphaBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["coding", "research", "analysis"],
    "llm_model": "gpt-4o",
    "personality": {
        "surface": {"bio": "테스트 에이전트", "style_sliders": {"formal": 0.8}},
        "deep": {}, "aspiration": {},
    },
}
_AGENT_B_BODY = {
    "display_name": f"BetaBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["coding", "design"],
}


def setup(state: dict) -> bool:
    """
    Principal A·B → Agent A·B → 상호 RIGHT 스와이프 → 매치 승인
    이 파일 안에서 모든 관계 단계 테스트를 완결한다 (서버 재시작 없이).
    """
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
        print(f"  ERROR setup: Agent A [{r.status_code}]: {r.text[:200]}")
        return False
    state["agent_a_id"] = r.json()["data"]["agent_id"]

    r = api_post("/v1/agents", JWT_B, _AGENT_B_BODY)
    if r.status_code != 200:
        print(f"  ERROR setup: Agent B [{r.status_code}]: {r.text[:200]}")
        return False
    state["agent_b_id"] = r.json()["data"]["agent_id"]

    # 상호 스와이프 → 매치 생성
    a, b = state["agent_a_id"], state["agent_b_id"]
    api_post(f"/v1/agents/{a}/swipe", JWT_A, {"target_id": b, "direction": "right"})
    r = api_post(f"/v1/agents/{b}/swipe", JWT_B, {"target_id": a, "direction": "right"})
    if r.status_code != 200:
        print(f"  ERROR setup: swipe B [{r.status_code}]: {r.text[:200]}")
        return False
    match = r.json().get("data", {}).get("match")
    if not match:
        print("  ERROR setup: 매치 생성 실패")
        return False
    state["match_id"] = match["match_id"]

    # 매치 승인
    r = api_post(f"/v1/matches/{state['match_id']}/approve", JWT_A)
    if r.status_code != 200:
        print(f"  ERROR setup: approve [{r.status_code}]: {r.text[:200]}")
        return False

    print(f"  SETUP Agent A: {state['agent_a_id']}")
    print(f"  SETUP Agent B: {state['agent_b_id']}")
    print(f"  SETUP Match:   {state['match_id']}")
    return True


def _date_cycle(state: dict, rating_stars: int = 4) -> bool:
    """데이트 1회: propose → end. True=성공."""
    match_id   = state["match_id"]
    agent_b_id = state["agent_b_id"]

    r = api_post(f"/v1/matches/{match_id}/dates", JWT_A, {
        "type": "coffee_chat",
        "scheduled_at": "2026-06-10T14:00:00Z",
    })
    if r.status_code != 200:
        return False
    date_id = r.json().get("data", {}).get("date_id")
    if not date_id:
        return False

    r = api_post(f"/v1/dates/{date_id}/end", JWT_A, {
        "outcome": "completed",
        "rated_agent_id": agent_b_id,
        "rating_stars": rating_stars,
        "rating_compatibility": rating_stars / 5.0,
    })
    return r.status_code == 200


# ── 5-1 ──────────────────────────────────────────────────────────────────────

def test_5_1_acquaintance(state: dict) -> bool:
    """
    end_date 1회 (rating_stars=4) → 200 OK
    Ground truth: sm.checkUpgrade → ACQUAINTANCE (relationships 테이블 직접 확인)
    """
    if not state.get("match_id"):
        return _fail("5-1 SKIP (no match_id)")

    ok = _date_cycle(state, rating_stars=4)
    state["done_dates"] = 1

    if ok:
        _ok("5-1 1st end_date 200 OK (→ ACQUAINTANCE in memory)")
    else:
        _fail("5-1 end_date failed")
    print("  INFO  5-1 relationship tier 확인은 relationships 테이블 직접 조회 필요 (API 미구현)")
    return ok


# ── 5-2 ──────────────────────────────────────────────────────────────────────

def test_5_2_colleague(state: dict) -> bool:
    """
    end_date 2회 추가 (총 3회) → 모두 200 OK
    Ground truth: successful_dates=3 → COLLEAGUE
    """
    if not state.get("match_id"):
        return _fail("5-2 SKIP (no match_id)")

    ok = True
    for i in range(2):
        if not _date_cycle(state, rating_stars=4):
            ok = _fail(f"5-2 date cycle {i+2} failed")
            break
        state["done_dates"] = state.get("done_dates", 1) + 1

    if ok:
        _ok(f"5-2 총 {state['done_dates']}회 end_date 200 OK (→ COLLEAGUE in memory)")
    print("  INFO  5-2 relationship tier 확인은 relationships 테이블 직접 조회 필요 (API 미구현)")
    return ok


# ── 5-3 ──────────────────────────────────────────────────────────────────────

def test_5_3_trusted_partner(state: dict) -> bool:
    """
    end_date 7회 추가 (총 10회, rating_stars=4) → 모두 200 OK
    Ground truth: successful_dates=10 + avg_rating≥4.0 → TRUSTED_PARTNER

    소프트 확인: 5회 이상 데이트 후 GET /v1/agents/{B_ID}의 trust_score 변화 여부
    (trust_score는 ScoreManager 계산 후 DB에 기록되면 non-null이 될 수 있음)
    """
    if not state.get("match_id"):
        return _fail("5-3 SKIP (no match_id)")

    ok = True
    for i in range(7):
        if not _date_cycle(state, rating_stars=4):
            ok = _fail(f"5-3 date cycle {state.get('done_dates', 3)+1} failed")
            break
        state["done_dates"] = state.get("done_dates", 3) + 1

    if ok:
        _ok(f"5-3 총 {state['done_dates']}회 end_date 200 OK (→ TRUSTED_PARTNER in memory)")

    # 소프트 확인: trust_score 변화 여부 (실패해도 suite 실패 아님)
    agent_b_id = state.get("agent_b_id")
    if agent_b_id:
        r = api_get(f"/v1/agents/{agent_b_id}", JWT_A)
        if r.status_code == 200:
            trust = r.json().get("data", {}).get("trust_score")
            if trust is not None:
                print(f"  INFO  5-3 trust_score={trust} (ScoreManager 계산 완료)")
            else:
                print("  INFO  5-3 trust_score=null (ScoreManager 미반영 또는 데이터포인트 부족)")

    print("  INFO  5-3 relationship tier 확인은 relationships 테이블 직접 조회 필요 (API 미구현)")
    return ok


# ── 5-4 ──────────────────────────────────────────────────────────────────────

def test_5_4_skip(state: dict) -> bool:
    print("  SKIP  5-4 Freeze — relationships 테이블 직접 조작 필요 (API 미구현)")
    return True


def main() -> int:
    state: dict = {}
    if not setup(state):
        print(f"[{SUITE_ID}] SETUP FAILED\n")
        return 1

    tests = [
        ("5-1 acquaintance (1 date)",      test_5_1_acquaintance),
        ("5-2 colleague (3 dates total)",  test_5_2_colleague),
        ("5-3 trusted_partner (10 total)", test_5_3_trusted_partner),
        ("5-4 freeze",                     test_5_4_skip),
    ]
    _, f = run_suite(SUITE_ID, tests, state)
    return f


if __name__ == "__main__":
    print(f"\n=== {SUITE_ID} ===")
    sys.exit(0 if main() == 0 else 1)
