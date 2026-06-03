"""
S2: 에이전트 CRUD
Guide: 시나리오 2 (2-1 ~ 2-5)

Setup  POST /v1/principals (JWT_A)        → Principal A 멱등 생성
2-1    POST /v1/agents                    → 200 agent_id·api_key·tier_badge=new_agent
2-2    GET  /v1/agents/{id}               → 200 프로필 필드 검증
2-3    PATCH /v1/agents/{id}              → 200 display_name 업데이트 확인
2-5    PATCH /v1/agents/{id} (JWT_B)      → 403 FORBIDDEN (타인 에이전트)

Skip: 2-4 (Free tier 5개 초과) — 에이전트 5개 사전 생성 필요, 별도 환경에서 수동 검증
"""
from __future__ import annotations
import sys, os
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

_RUN_ID = uuid4().hex[:6]

from helpers import (
    api_get, api_post, api_patch,
    check_status, check_field, check_not_none, check_error_code,
    run_suite, _ok, _fail,
    make_jwt,
)

# 실행마다 신규 UUID → principal 에이전트 누적 방지
JWT_A = make_jwt(str(uuid4()), f"a-{_RUN_ID}@test.local")
JWT_B = make_jwt(str(uuid4()), f"b-{_RUN_ID}@test.local")

SUITE_ID = "S2-AGENT-CRUD"

_CREATE_BODY = {
    "display_name": f"AlphaBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["coding", "research", "analysis"],
    "available_timezones": ["Asia/Seoul"],
    "llm_model": "gpt-4o",
    "personality": {
        "surface": {
            "bio": "꼼꼼한 분석가입니다.",
            "style_sliders": {"formal": 0.8, "verbose": 0.4, "bold": 0.6},
        },
        "deep": {
            "thinking_style": "분석적",
            "values": ["정확성", "신뢰"],
            "conflict_handling": "데이터 기반 논의",
        },
        "aspiration": {
            "collaboration_goals": ["코드 품질 향상"],
            "interest_domains": ["backend", "data"],
        },
    },
}


def setup(state: dict) -> bool:
    """Principal A 멱등 생성 — 이미 존재하면 기존 레코드 반환."""
    resp = api_post("/v1/principals", JWT_A, {"name": "Test User"})
    if resp.status_code != 200:
        print(f"  ERROR setup: POST /v1/principals [{resp.status_code}]: {resp.text[:200]}")
        return False
    return True


def test_2_1_create_agent(state: dict) -> bool:
    """POST /v1/agents → agent_id·api_key·display_name·tier_badge=new_agent"""
    resp = api_post("/v1/agents", JWT_A, _CREATE_BODY)
    ok = check_status("2-1 create agent", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_not_none("2-1 agent_id",    data, "agent_id")
    ok &= check_not_none("2-1 api_key",     data, "api_key")
    ok &= check_field("2-1 display_name",   data, "display_name", _CREATE_BODY["display_name"])
    ok &= check_field("2-1 visibility",     data, "visibility",   "PUBLIC")
    ok &= check_field("2-1 tier_badge",     data, "tier_badge",   "new_agent")
    if data.get("agent_id"):
        state["agent_a_id"] = data["agent_id"]
    return ok


def test_2_2_get_profile(state: dict) -> bool:
    """GET /v1/agents/{id} → 200 프로필 필드·bio·capability_tags 확인"""
    agent_id = state.get("agent_a_id")
    if not agent_id:
        return _fail("2-2 SKIP (no agent_a_id from 2-1)")
    resp = api_get(f"/v1/agents/{agent_id}", JWT_A)
    ok = check_status("2-2 get profile", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_field("2-2 display_name",  data, "display_name", _CREATE_BODY["display_name"])
    ok &= check_field("2-2 tier_badge",    data, "tier_badge",   "new_agent")
    ok &= check_field("2-2 date_count",    data, "date_count",   0)
    ok &= check_field("2-2 trust_score",   data, "trust_score",  None)
    ok &= check_field("2-2 bio",           data, "bio",          "꼼꼼한 분석가입니다.")
    tags = data.get("capability_tags", [])
    ok &= check_field("2-2 tags count", {"n": len(tags)}, "n", 3)
    return ok


def test_2_3_update_profile(state: dict) -> bool:
    """PATCH /v1/agents/{id} → display_name·visibility 업데이트 확인"""
    agent_id = state.get("agent_a_id")
    if not agent_id:
        return _fail("2-3 SKIP (no agent_a_id)")
    resp = api_patch(f"/v1/agents/{agent_id}", JWT_A, {
        "display_name": f"AlphaBot-{_RUN_ID}-v2",
        "visibility": "RESTRICTED",
        "capability_tags": ["coding", "research", "architecture"],
    })
    ok = check_status("2-3 update profile", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_field("2-3 display_name updated", data, "display_name", f"AlphaBot-{_RUN_ID}-v2")
    # visibility 반환값은 소문자("restricted") 또는 대문자 둘 다 허용
    vis = str(data.get("visibility", "")).lower()
    if vis == "restricted":
        _ok("2-3 visibility=restricted")
    else:
        ok = _fail("2-3 visibility", f"got={data.get('visibility')!r}")
    return ok


def test_2_5_wrong_owner_403(state: dict) -> bool:
    """PATCH /v1/agents/{agent_a_id} (JWT_B) → 403 FORBIDDEN"""
    agent_id = state.get("agent_a_id")
    if not agent_id:
        return _fail("2-5 SKIP (no agent_a_id)")

    # Principal B를 DB에 먼저 생성해야 get_principal(JWT_B)가 성공한다
    api_post("/v1/principals", JWT_B, {"name": "User B"})

    resp = api_patch(f"/v1/agents/{agent_id}", JWT_B, {"display_name": "Hacked"})
    ok = check_status("2-5 wrong owner HTTP", resp, 403)
    if ok:
        ok &= check_error_code("2-5 error code", resp.json(), "FORBIDDEN")
    return ok


def main() -> int:
    state: dict = {}
    if not setup(state):
        print(f"[{SUITE_ID}] SETUP FAILED — backend가 실행 중인지 확인하세요.\n")
        return 1

    tests = [
        ("2-1 create agent",   test_2_1_create_agent),
        ("2-2 get profile",    test_2_2_get_profile),
        ("2-3 update profile", test_2_3_update_profile),
        ("2-5 wrong owner",    test_2_5_wrong_owner_403),
    ]
    _, f = run_suite(SUITE_ID, tests, state)
    return f


if __name__ == "__main__":
    print(f"\n=== {SUITE_ID} ===")
    sys.exit(0 if main() == 0 else 1)
