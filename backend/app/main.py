from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .auth.auth_middleware import AuthMiddleware
from .auth.error_handler_middleware import ErrorHandlerMiddleware
from .config import settings
from .deps import init_singletons
from .handlers import (
    agent_profile_handler,
    auth_handler,
    date_handler,
    feed_handler,
    match_handler,
    message_handler,
    principal_handler,
)
from .transport import ws_transport


@asynccontextmanager
async def lifespan(app: FastAPI):
    # pydantic-settings는 os.environ을 채우지 않으므로 모델 레이어가 읽을 수 있도록 주입한다.
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    await db.init_pool()
    init_singletons()
    yield
    await db.close_pool()


app = FastAPI(title="Agentinder API", version="1.0.0", lifespan=lifespan)

# 미들웨어 등록: add_middleware 는 LIFO — 나중에 추가한 것이 가장 바깥에서 먼저 실행된다.
# 요청 흐름: CORS → ErrorHandler → Auth → Handler
# CORS 를 가장 바깥에 두어야 preflight(OPTIONS, Authorization 헤더 없음)가
# AuthMiddleware 의 401 에 막히지 않고 응답된다.
app.add_middleware(AuthMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용 전체 허용 — 배포 시 origin 목록 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_handler.router)
app.include_router(principal_handler.router)
app.include_router(agent_profile_handler.router)
app.include_router(feed_handler.router)
app.include_router(match_handler.router)
app.include_router(message_handler.router)
app.include_router(date_handler.router)
app.include_router(ws_transport.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
