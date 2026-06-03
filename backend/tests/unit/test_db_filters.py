"""
test_db_filters.py — get_agents_by_filters 동적 SQL 빌더 정합성 단위 테스트.

테스트 대상: backend/app/db.py::get_agents_by_filters
호출 위치: pytest 수집 시 자동 실행.

실제 DB 없이 get_pool 을 mock 하여 생성된 SQL 문자열과 바인딩 파라미터를
캡처하고, 플레이스홀더($N) 번호가 params 개수와 정확히 1:1 대응하는지 검증한다.
(동적 쿼리에서 가장 흔한 버그인 플레이스홀더 어긋남을 방지한다.)
"""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app import db


async def _capture(**kwargs) -> dict:
    captured: dict = {}

    async def fake_fetch(query, *params):
        captured["query"] = query
        captured["params"] = params
        return []

    pool = MagicMock()
    pool.fetch = fake_fetch
    with patch("app.db.get_pool", return_value=pool):
        await db.get_agents_by_filters(uuid4(), **kwargs)
    return captured


def _assert_placeholders_consistent(captured: dict) -> None:
    nums = {int(n) for n in re.findall(r"\$(\d+)", captured["query"])}
    # $1..$N 이 빠짐없이 등장하고, N == 바인딩 파라미터 개수
    assert nums == set(range(1, len(captured["params"]) + 1)), (
        f"placeholders={sorted(nums)} params={len(captured['params'])}\n{captured['query']}"
    )


class TestGetAgentsByFiltersSQL:
    async def test_no_filters_uses_single_param(self) -> None:
        cap = await _capture()
        assert len(cap["params"]) == 1  # exclude_agent_id 만
        _assert_placeholders_consistent(cap)

    async def test_all_value_filters_placeholder_consistency(self) -> None:
        cap = await _capture(
            capability_tags=["research", "coding"],
            trust_min=0.1,
            trust_max=0.9,
            style="verbose",
            domain="ml",
            availability="available",
            search_q="foo",
        )
        # 값 바인딩 필터: exclude + trust_min + trust_max + domain + search_q + capability = 6
        # (style, availability 는 컬럼 조건만 추가하고 파라미터를 쓰지 않음)
        assert len(cap["params"]) == 6
        _assert_placeholders_consistent(cap)

    async def test_capability_only(self) -> None:
        cap = await _capture(capability_tags=["research"])
        # exclude(1) + capability(1)
        assert len(cap["params"]) == 2
        _assert_placeholders_consistent(cap)

    async def test_style_and_availability_add_no_params(self) -> None:
        cap = await _capture(style="formal", availability="available")
        assert len(cap["params"]) == 1  # exclude 만
        _assert_placeholders_consistent(cap)
        assert "aper.style_formal >= 50" in cap["query"]
        assert "agent_availability" in cap["query"]

    async def test_search_q_reuses_single_placeholder(self) -> None:
        cap = await _capture(search_q="foo")
        # display_name / bio / domain_interest 세 컬럼이 같은 플레이스홀더를 공유
        assert len(cap["params"]) == 2  # exclude + search_q
        _assert_placeholders_consistent(cap)
        assert cap["params"][1] == "%foo%"
