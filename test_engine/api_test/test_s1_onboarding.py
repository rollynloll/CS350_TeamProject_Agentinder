"""
S1: Onboarding — Principal 계정 생성
Guide: 시나리오 1 (1-1 ~ 1-5)

1-1  GET  /healthz                        → 200 {"status": "ok"}
1-2  POST /v1/principals                  → 200 principal_id, plan=FREE (멱등)
1-3  GET  /v1/agents                      → 200 data=list
1-4  GET  /v1/agents (invalid token)      → 401 UNAUTHORIZED
1-5  GET  /v1/agents (no token)           → 401 UNAUTHORIZED
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

from helpers import (
    JWT_A, EMAIL_A, PRINCIPAL_A_ID,
    api_get, api_post,
    check_status, check_field, check_not_none, check_truthy, check_error_code,
    run_suite,
)

SUITE_ID = "S1-ONBOARDING"


def test_1_1_healthcheck(state: dict) -> bool:
    """GET /healthz → 200 {"status": "ok"}"""
    resp = api_get("/healthz")
    ok = check_status("1-1 healthcheck", resp, 200)
    if ok:
        ok &= check_field("1-1 status field", resp.json(), "status", "ok")
    return ok


def test_1_2_create_principal(state: dict) -> bool:
    """POST /v1/principals → 200 principal_id·email·plan=FREE (멱등)"""
    resp = api_post(
        "/v1/principals", JWT_A,
        {"name": "Test User", "email": EMAIL_A},
    )
    ok = check_status("1-2 create principal", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_field("1-2 principal_id", data, "principal_id", PRINCIPAL_A_ID)
    # email 은 멱등 엔드포인트라 기존 레코드 email이 반환될 수 있으므로 존재 여부만 확인
    ok &= check_not_none("1-2 email present", data, "email")
    ok &= check_field("1-2 plan=FREE",    data, "plan",         "FREE")
    ok &= check_not_none("1-2 created_at", data, "created_at")
    return ok


def test_1_3_list_agents(state: dict) -> bool:
    """GET /v1/agents → 200, data is a list"""
    resp = api_get("/v1/agents", JWT_A)
    ok = check_status("1-3 list agents", resp, 200)
    if not ok:
        return False
    body = resp.json()
    ok &= check_truthy("1-3 data key exists", "data" in body, "'data' missing")
    ok &= check_truthy("1-3 data is list", isinstance(body.get("data"), list),
                       f"data type={type(body.get('data'))}")
    return ok


def test_1_4_invalid_token(state: dict) -> bool:
    """GET /v1/agents (invalid token) → 401 UNAUTHORIZED"""
    resp = api_get("/v1/agents", "invalid_token")
    ok = check_status("1-4 invalid token", resp, 401)
    if ok:
        ok &= check_error_code("1-4 error code", resp.json(), "UNAUTHORIZED")
    return ok


def test_1_5_no_token(state: dict) -> bool:
    """GET /v1/agents (no token) → 401 UNAUTHORIZED"""
    resp = api_get("/v1/agents")
    ok = check_status("1-5 no token", resp, 401)
    if ok:
        ok &= check_error_code("1-5 error code", resp.json(), "UNAUTHORIZED")
    return ok


def main() -> int:
    state: dict = {}
    tests = [
        ("1-1 healthcheck",      test_1_1_healthcheck),
        ("1-2 create principal", test_1_2_create_principal),
        ("1-3 list agents",      test_1_3_list_agents),
        ("1-4 invalid token",    test_1_4_invalid_token),
        ("1-5 no token",         test_1_5_no_token),
    ]
    _, f = run_suite(SUITE_ID, tests, state)
    return f


if __name__ == "__main__":
    print(f"\n=== {SUITE_ID} ===")
    sys.exit(0 if main() == 0 else 1)
