from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .auth.auth_middleware import AuthMiddleware
from .auth.error_handler_middleware import ErrorHandlerMiddleware
from .deps import init_singletons
from .handlers import (
    agent_profile_handler,
    auth_handler,
    date_handler,
    feed_handler,
    match_handler,
    message_handler,
)
from .transport import ws_transport


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    init_singletons()
    yield
    await db.close_pool()


app = FastAPI(title="Agentinder API", version="1.0.0", lifespan=lifespan)

# CORS — 개발 중 전체 오리진 허용, 배포 시 origins 목록 제한 필요
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 미들웨어: add_middleware 역순 적용 → 요청 흐름: ErrorHandler → Auth → Handler
app.add_middleware(AuthMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

app.include_router(auth_handler.router)
app.include_router(agent_profile_handler.router)
app.include_router(feed_handler.router)
app.include_router(match_handler.router)
app.include_router(message_handler.router)
app.include_router(date_handler.router)
app.include_router(ws_transport.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
