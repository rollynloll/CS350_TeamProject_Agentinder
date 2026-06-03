"""
Shared helpers for api_test suite.

JWT secret is loaded from backend/.env (SUPABASE_JWT_SECRET).
The server decodes with verify_aud=False, so no audience claim is needed.
"""
from __future__ import annotations

import os
import traceback
from typing import Any

import httpx
from jose import jwt as jose_jwt

# ── Constants ─────────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000"
WS_BASE  = "ws://localhost:8000"

# Fixed principal UUIDs — match make_dev_jwt.py --sub values
PRINCIPAL_A_ID = "fdfd49a8-bfe2-456e-a662-2273f6aae4d6"
PRINCIPAL_B_ID = "b1b1b1b1-bfe2-456e-a662-2273f6aae4d6"
EMAIL_A        = "test@example.com"
EMAIL_B        = "b@example.com"

_TIMEOUT = httpx.Timeout(15.0)

# ── JWT secret ────────────────────────────────────────────────────────────────

def _load_jwt_secret() -> str:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("SUPABASE_JWT_SECRET="):
                    val = line.split("=", 1)[1].strip()
                    return val.strip('"').strip("'")
    return os.environ.get("SUPABASE_JWT_SECRET", "")


JWT_SECRET = _load_jwt_secret()


def make_jwt(principal_id: str, email: str) -> str:
    """Encode JWT with sub, role=authenticated, email (server uses verify_aud=False)."""
    return jose_jwt.encode(
        {"sub": principal_id, "role": "authenticated", "email": email},
        JWT_SECRET,
        algorithm="HS256",
    )


JWT_A = make_jwt(PRINCIPAL_A_ID, EMAIL_A)
JWT_B = make_jwt(PRINCIPAL_B_ID, EMAIL_B)

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers(token: str | None, json_ct: bool = True) -> dict:
    h: dict = {}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if json_ct:
        h["Content-Type"] = "application/json"
    return h


def api_get(path: str, token: str | None = None, **kw) -> httpx.Response:
    return httpx.get(
        f"{BASE_URL}{path}",
        headers=_headers(token, json_ct=False),
        timeout=_TIMEOUT, **kw,
    )


def api_post(path: str, token: str | None = None, body: dict | None = None, **kw) -> httpx.Response:
    return httpx.post(
        f"{BASE_URL}{path}",
        headers=_headers(token),
        json=body,
        timeout=_TIMEOUT, **kw,
    )


def api_patch(path: str, token: str | None = None, body: dict | None = None, **kw) -> httpx.Response:
    return httpx.patch(
        f"{BASE_URL}{path}",
        headers=_headers(token),
        json=body,
        timeout=_TIMEOUT, **kw,
    )

# ── Assert helpers ────────────────────────────────────────────────────────────

def _ok(label: str) -> bool:
    print(f"  PASS  {label}")
    return True


def _fail(label: str, detail: str = "") -> bool:
    print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
    return False


def check_status(label: str, resp: httpx.Response, expected: int) -> bool:
    if resp.status_code == expected:
        return _ok(f"{label} [HTTP {resp.status_code}]")
    snippet = resp.text[:300].replace("\n", " ")
    return _fail(label, f"HTTP {resp.status_code} (expected {expected}): {snippet}")


def check_field(label: str, data: dict, field: str, expected: Any) -> bool:
    got = data.get(field)
    if got == expected:
        return _ok(f"{label} [{field}={expected!r}]")
    return _fail(label, f"{field}: got={got!r}, expected={expected!r}")


def check_not_none(label: str, data: dict, field: str) -> bool:
    if data.get(field) is not None:
        return _ok(f"{label} [{field} present]")
    return _fail(label, f"{field} is None or missing")


def check_truthy(label: str, value: Any, detail: str = "") -> bool:
    if value:
        return _ok(label)
    return _fail(label, detail or f"got {value!r}")


def check_error_code(label: str, body: dict, expected_code: str) -> bool:
    err = (body.get("error") or {})
    got = err.get("code")
    if got == expected_code:
        return _ok(f"{label} [error.code={expected_code!r}]")
    return _fail(label, f"error.code: got={got!r}, expected={expected_code!r}")

# ── Suite runner ──────────────────────────────────────────────────────────────

def run_suite(suite_id: str, tests: list[tuple[str, Any]], state: dict) -> tuple[int, int]:
    passed = failed = 0
    for label, fn in tests:
        try:
            ok = fn(state)
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR {label} — {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n[{suite_id}] {passed} passed, {failed} failed\n")
    return passed, failed
