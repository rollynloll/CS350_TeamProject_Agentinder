from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

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
