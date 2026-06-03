#!/usr/bin/env python3
"""OpenAI API 키 연결 상태 확인.

backend/.env(또는 환경변수)의 OPENAI_API_KEY 로 OpenAI API에 가벼운 요청
(GET /v1/models, 과금 없음)을 보내 키 유효성을 확인한다.

사용법 (backend 디렉토리에서 venv 활성화 후):
    python scripts/check_openai_key.py
종료 코드: 0 정상 / 1 키 없음 / 2 네트워크 오류 / 3 인증 실패 / 4 기타
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

try:
    from dotenv import dotenv_values
except ImportError:  # python-dotenv 미설치 방어
    dotenv_values = None


def resolve_key() -> str | None:
    """환경변수 → backend/.env 순으로 OPENAI_API_KEY 를 찾는다."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if dotenv_values and env_path.is_file():
        return dotenv_values(env_path).get("OPENAI_API_KEY") or None
    return None


def main() -> int:
    key = resolve_key()
    if not key:
        print("❌ OPENAI_API_KEY 가 비어 있습니다. (.env 또는 환경변수를 확인하세요)")
        return 1

    masked = f"{key[:7]}…{key[-4:]}" if len(key) > 12 else "***"
    print(f"키 감지: {masked}")

    try:
        res = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        print(f"❌ 네트워크 오류: {exc}")
        return 2

    if res.status_code == 200:
        count = len(res.json().get("data", []))
        print(f"✅ 연결 정상 (HTTP 200, 접근 가능한 모델 {count}개)")
        return 0
    if res.status_code == 401:
        print("❌ 인증 실패 (HTTP 401) — 키가 유효하지 않거나 만료되었습니다.")
        return 3
    print(f"⚠️ 예상치 못한 응답: HTTP {res.status_code} — {res.text[:200]}")
    return 4


if __name__ == "__main__":
    sys.exit(main())
