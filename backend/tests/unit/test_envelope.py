"""
test_envelope.py — envelope() 함수 및 ErrorHandlerMiddleware 단위 테스트.

테스트 대상: backend/app/auth/error_handler_middleware.py
호출 위치: pytest 수집 시 자동 실행.
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.error_handler_middleware import ErrorHandlerMiddleware, envelope


class TestEnvelopeStructure:
    """envelope() 반환 구조 테스트."""

    def test_envelope_returns_dict_with_three_keys(self) -> None:
        result = envelope()
        assert set(result.keys()) == {"data", "meta", "error"}

    def test_envelope_data_defaults_to_none(self) -> None:
        result = envelope()
        assert result["data"] is None

    def test_envelope_meta_defaults_to_empty_dict(self) -> None:
        result = envelope()
        assert result["meta"] == {}

    def test_envelope_error_defaults_to_none(self) -> None:
        result = envelope()
        assert result["error"] is None


class TestEnvelopeDataField:
    """envelope() data 필드 테스트."""

    def test_envelope_data_set_with_dict(self) -> None:
        payload = {"items": [1, 2, 3], "next_cursor": None}
        result = envelope(data=payload)
        assert result["data"] == payload

    def test_envelope_data_set_with_string(self) -> None:
        result = envelope(data="hello")
        assert result["data"] == "hello"

    def test_envelope_data_set_with_list(self) -> None:
        result = envelope(data=[1, 2, 3])
        assert result["data"] == [1, 2, 3]

    def test_envelope_data_set_with_none_explicitly(self) -> None:
        result = envelope(data=None)
        assert result["data"] is None

    def test_envelope_data_set_with_empty_dict(self) -> None:
        result = envelope(data={})
        assert result["data"] == {}

    def test_envelope_data_set_with_integer(self) -> None:
        result = envelope(data=42)
        assert result["data"] == 42

    def test_envelope_data_set_with_boolean(self) -> None:
        result = envelope(data=True)
        assert result["data"] is True

    def test_envelope_data_nested_structure(self) -> None:
        payload = {"match": {"match_id": "abc-123"}}
        result = envelope(data=payload)
        assert result["data"]["match"]["match_id"] == "abc-123"


class TestEnvelopeMetaField:
    """envelope() meta 필드 테스트."""

    def test_envelope_meta_set_with_dict(self) -> None:
        meta = {"page": 1, "total": 100}
        result = envelope(meta=meta)
        assert result["meta"] == meta

    def test_envelope_meta_none_becomes_empty_dict(self) -> None:
        result = envelope(meta=None)
        assert result["meta"] == {}

    def test_envelope_meta_empty_dict_allowed(self) -> None:
        result = envelope(meta={})
        assert result["meta"] == {}


class TestEnvelopeErrorField:
    """envelope() error 필드 테스트."""

    def test_envelope_error_set_with_dict(self) -> None:
        err = {"code": "NOT_FOUND", "message": "리소스를 찾을 수 없습니다", "status": 404}
        result = envelope(error=err)
        assert result["error"] == err

    def test_envelope_error_none_allowed(self) -> None:
        result = envelope(error=None)
        assert result["error"] is None


class TestEnvelopeHappyPath:
    """정상 응답 시나리오 테스트 (data 있고 error 없음)."""

    def test_swipe_success_response_shape(self) -> None:
        result = envelope(data={"swiped": True, "match": None})
        assert result["data"]["swiped"] is True
        assert result["data"]["match"] is None
        assert result["error"] is None
        assert result["meta"] == {}

    def test_feed_response_with_items(self) -> None:
        items = [{"agent_id": "aaa", "compatibility_total": 0.9}]
        result = envelope(data={"items": items, "next_cursor": None})
        assert len(result["data"]["items"]) == 1
        assert result["data"]["next_cursor"] is None

    def test_meta_does_not_mutate_between_calls(self) -> None:
        """meta 기본값이 호출 간 공유되지 않는다."""
        r1 = envelope()
        r2 = envelope()
        r1["meta"]["injected"] = True
        assert "injected" not in r2["meta"]


def _make_error_handler_app(raiser) -> FastAPI:
    """ErrorHandlerMiddleware가 붙은 테스트용 FastAPI 앱을 생성한다."""
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)

    @app.get("/test")
    async def test_route():
        raise raiser

    return app


class TestErrorHandlerMiddleware:
    """ErrorHandlerMiddleware.dispatch 예외→envelope 변환 테스트."""

    async def test_key_error_returns_404(self) -> None:
        app = _make_error_handler_app(KeyError("리소스 없음"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["data"] is None
        assert body["meta"] == {}

    async def test_permission_error_returns_403(self) -> None:
        app = _make_error_handler_app(PermissionError("금지됨"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    async def test_value_error_returns_400(self) -> None:
        app = _make_error_handler_app(ValueError("잘못된 값"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "BAD_REQUEST"

    async def test_runtime_error_returns_500(self) -> None:
        app = _make_error_handler_app(RuntimeError("서버 오류"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
        assert resp.status_code == 500
        assert resp.json()["error"]["code"] == "INTERNAL_ERROR"

    async def test_unknown_error_returns_500(self) -> None:
        app = _make_error_handler_app(Exception("알 수 없는 오류"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
        assert resp.status_code == 500
        assert resp.json()["error"]["code"] == "INTERNAL_ERROR"

    async def test_error_response_is_valid_json(self) -> None:
        app = _make_error_handler_app(KeyError("json 테스트"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
        assert resp.headers["content-type"].startswith("application/json")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "error" in body

    async def test_error_message_included_in_response(self) -> None:
        app = _make_error_handler_app(ValueError("구체적인 오류 메시지"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
        assert "구체적인 오류 메시지" in resp.json()["error"]["message"]

    async def test_successful_request_passes_through(self) -> None:
        """정상 요청은 미들웨어를 통과해 핸들러 응답이 그대로 반환된다."""
        app = FastAPI()
        app.add_middleware(ErrorHandlerMiddleware)

        @app.get("/ok")
        async def ok_route():
            return {"status": "ok"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ok")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
