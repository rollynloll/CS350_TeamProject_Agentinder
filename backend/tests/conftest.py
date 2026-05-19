"""
conftest.py — backend/tests 공통 픽스처 및 환경 설정.

호출 위치: pytest 수집 시 자동으로 읽힘.
역할:
  1. sys.path 에 프로젝트 루트(models/ 포함)를 추가
  2. config.py 가 .env 없이 임포트될 수 있도록 os.environ 에 fake 값 세팅
  3. 공통 픽스처(event_bus, fake UUID 등) 제공
"""
from __future__ import annotations

import os
import sys

# ── 1. sys.path 설정: 프로젝트 루트 추가 ─────────────────────────────────
# backend/tests/conftest.py 기준: ../../ 가 프로젝트 루트
_TESTS_DIR = os.path.dirname(__file__)
_BACKEND_DIR = os.path.dirname(_TESTS_DIR)
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

for _p in [_PROJECT_ROOT, _BACKEND_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 2. config.py ValidationError 방지 — 임포트 전에 env 세팅 ─────────────
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "fake-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "fake-jwt-secret-for-testing-only")
os.environ.setdefault("DATABASE_URL", "postgresql://fake:fake@localhost/fake")
os.environ.setdefault("OPENAI_API_KEY", "fake-openai-key")

import pytest

from app.pubsub.event_bus import EventBus


@pytest.fixture
def event_bus() -> EventBus:
    """독립적인 EventBus 인스턴스를 반환한다."""
    return EventBus()
