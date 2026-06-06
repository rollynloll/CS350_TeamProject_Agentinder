"""
Flow Test 공통 헬퍼

기능:
  - agent_profiles/*.json 로드
  - JWT 발급 (실행마다 신규 UUID)
  - HTTP 클라이언트 (api_test/helpers.py와 동일 패턴)
  - WS 데이트 세션 (asyncio)
  - 상태(state) JSON 저장·로드
  - DB 리셋 (docker exec → DELETE FROM principals CASCADE)
  - 구조화된 로거
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from jose import jwt as jose_jwt

# ── 경로 ─────────────────────────────────────────────────────────────────────

FLOW_DIR   = Path(__file__).parent
PROFILE_DIR = FLOW_DIR / "agent_profiles"
LOG_DIR    = FLOW_DIR / "logs"
STATE_FILE = FLOW_DIR / "flow_state.json"

LOG_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(FLOW_DIR.parent.parent))  # 프로젝트 루트

# ── 상수 ─────────────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000"
WS_BASE  = "ws://localhost:8000"
_TIMEOUT = httpx.Timeout(30.0)

# WS 데이트 세션 메시지 턴 수
# 1 WS send = 유저 메시지 1건 + LLM 응답 1건 = DB 메시지 2건
# 5 turns × 2 = 대화 10건 (고정)
ASYNC_DATE_TURNS = 5   # S2: 비동기 데이트
SYNC_DATE_TURNS  = 5   # S4: 동기 데이트

try:
    import websockets as _ws_mod
    HAS_WS = True
except ImportError:
    HAS_WS = False

# ── JWT secret ────────────────────────────────────────────────────────────────

def _load_jwt_secret() -> str:
    env_path = FLOW_DIR.parent.parent / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("SUPABASE_JWT_SECRET="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("SUPABASE_JWT_SECRET", "")


JWT_SECRET = _load_jwt_secret()


def make_jwt(principal_id: str, email: str) -> str:
    return jose_jwt.encode(
        {"sub": principal_id, "role": "authenticated", "email": email},
        JWT_SECRET,
        algorithm="HS256",
    )


def new_user_credentials(n: int) -> tuple[str, str, str]:
    """(principal_id, email, jwt) 신규 발급."""
    pid   = str(uuid4())
    email = f"flowuser{n}-{pid[:8]}@flow.test"
    jwt   = make_jwt(pid, email)
    return pid, email, jwt

# ── HTTP ──────────────────────────────────────────────────────────────────────

def _headers(token: str | None, json_ct: bool = True) -> dict:
    h: dict = {}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if json_ct:
        h["Content-Type"] = "application/json"
    return h


def api_get(path: str, token: str | None = None) -> httpx.Response:
    return httpx.get(f"{BASE_URL}{path}", headers=_headers(token, False), timeout=_TIMEOUT)


def api_post(path: str, token: str | None = None, body: dict | None = None) -> httpx.Response:
    return httpx.post(f"{BASE_URL}{path}", headers=_headers(token), json=body, timeout=_TIMEOUT)


def api_patch(path: str, token: str | None = None, body: dict | None = None) -> httpx.Response:
    return httpx.patch(f"{BASE_URL}{path}", headers=_headers(token), json=body, timeout=_TIMEOUT)

# ── 프로필 로더 ───────────────────────────────────────────────────────────────

def load_profile(user_n: int, agent_type: str) -> dict:
    """agent_profiles/user_{N}/agent_{type}.json 로드."""
    path = PROFILE_DIR / f"user_{user_n}" / f"agent_{agent_type}.json"
    return json.loads(path.read_text(encoding="utf-8"))

# ── 상태 저장·로드 ────────────────────────────────────────────────────────────

def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"users": {}, "async_matches": [], "sync_matches": []}


def empty_state() -> dict:
    return {"users": {}, "async_matches": [], "sync_matches": []}


# ── DB 리셋 ───────────────────────────────────────────────────────────────────

# docker exec 로 psql 을 호출할 컨테이너·DB 정보
_DB_CONTAINER = "backend-db-1"
_DB_USER      = "agentinder"
_DB_NAME      = "agentinder"


def reset_principals(principal_ids: list[str], logger: logging.Logger | None = None) -> bool:
    """
    주어진 principal_id 목록을 DB에서 삭제한다.

    principals 테이블에 ON DELETE CASCADE 가 전파되므로
    하위 테이블(agents, swipes, matches, dates, messages, 관계 등)이
    자동으로 모두 삭제된다.

    docker exec 로 컨테이너 내 psql 을 호출하므로
    backend Docker 가 실행 중이어야 한다.
    """
    log = logger or logging.getLogger(__name__)

    if not principal_ids:
        log.debug("reset_principals: 삭제할 principal 없음 — 스킵")
        return True

    # uuid 배열 리터럴 생성: ARRAY['id1','id2',...]::uuid[]
    arr = "ARRAY[" + ",".join(f"'{pid}'" for pid in principal_ids) + "]::uuid[]"
    sql = f"DELETE FROM principals WHERE principal_id = ANY({arr});"

    log.info("DB 리셋: %d명 principal + CASCADE 삭제 중…", len(principal_ids))
    result = subprocess.run(
        [
            "docker", "exec", _DB_CONTAINER,
            "psql", "-U", _DB_USER, "-d", _DB_NAME, "-c", sql,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        deleted = result.stdout.strip()   # e.g. "DELETE 4"
        log.info("DB 리셋 완료: %s", deleted)
        return True
    else:
        log.error("DB 리셋 실패 (returncode=%d): %s",
                  result.returncode, result.stderr.strip()[:300])
        return False


def collect_principal_ids(state: dict) -> list[str]:
    """state dict 에서 모든 principal_id 를 수집한다."""
    return [
        u["principal_id"]
        for u in state.get("users", {}).values()
        if u.get("principal_id")
    ]

# ── 로거 ─────────────────────────────────────────────────────────────────────

def make_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", "%H:%M:%S")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fh  = logging.FileHandler(LOG_DIR / f"{name}_{ts}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

# ── 대화 로그 파일 ────────────────────────────────────────────────────────────

def write_conversation_log(
    filename: str,
    match_id: str,
    agent_a_id: str,
    agent_b_id: str,
    label_a: str,
    label_b: str,
    messages: list[dict],
) -> Path:
    """messages: GET /v1/matches/{M}/messages 응답 items"""
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOG_DIR / f"{filename}_{ts}.log"

    lines = [
        f"대화 기록  {ts}",
        f"match_id : {match_id}",
        f"agent_a  : {agent_a_id}  ({label_a})",
        f"agent_b  : {agent_b_id}  ({label_b})",
        "─" * 60,
    ]
    for msg in messages:
        sid     = msg.get("sender_agent_id", "")
        speaker = label_a if sid == agent_a_id else label_b if sid == agent_b_id else sid[:8]
        ts_msg  = (msg.get("created_at") or "")[:19]
        lines.append(f"[{ts_msg}] {speaker}: {msg.get('content', '')}")
    lines.append("─" * 60)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

# ── WS 데이트 세션 ────────────────────────────────────────────────────────────

async def _ws_date_session(
    jwt_a: str, jwt_b: str,
    agent_a_id: str, agent_b_id: str,
    match_id: str, date_id: str,
    turns: list[tuple[str, str]],   # [(sender='a'|'b', content), ...]
) -> dict:
    """
    양측 WS 연결 → join_date → 메시지 교환.
    turns: [('a', '첫 메시지'), ('b', '두 번째'), ...]
    반환: {'joined': bool, 'messages': [message_sent 이벤트, ...]}
    """
    if not HAS_WS:
        return {"joined": False, "messages": []}

    import websockets

    results: dict = {"joined": False, "messages": []}
    url_a = f"{WS_BASE}/v1/ws?token={jwt_a}"
    url_b = f"{WS_BASE}/v1/ws?token={jwt_b}"

    async def _recv_until(ws, event_name: str, timeout: float = 15.0) -> dict:
        for _ in range(8):
            try:
                raw = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                if raw.get("event") == event_name:
                    return raw
            except asyncio.TimeoutError:
                break
        return {}

    async with websockets.connect(url_a) as ws_a:
        await ws_a.send(json.dumps({"event": "subscribe", "topic": f"date.{date_id}", "payload": {}}))
        await asyncio.wait_for(ws_a.recv(), timeout=5)

        await ws_a.send(json.dumps({
            "topic": f"date.{date_id}", "event": "join_date",
            "payload": {"date_id": str(date_id), "agent_id": str(agent_a_id)},
        }))
        join_a = json.loads(await asyncio.wait_for(ws_a.recv(), timeout=5))

        async with websockets.connect(url_b) as ws_b:
            await ws_b.send(json.dumps({"event": "subscribe", "topic": f"date.{date_id}", "payload": {}}))
            await asyncio.wait_for(ws_b.recv(), timeout=5)

            await ws_b.send(json.dumps({
                "topic": f"date.{date_id}", "event": "join_date",
                "payload": {"date_id": str(date_id), "agent_id": str(agent_b_id)},
            }))
            join_b = json.loads(await asyncio.wait_for(ws_b.recv(), timeout=5))

            results["joined"] = join_b.get("started", False)

            for sender, content in turns:
                ws   = ws_a if sender == "a" else ws_b
                a_id = agent_a_id if sender == "a" else agent_b_id
                await ws.send(json.dumps({
                    "topic": f"chat.{match_id}", "event": "send_message",
                    "payload": {"match_id": str(match_id), "agent_id": str(a_id), "content": content},
                }))
                msg = await _recv_until(ws, "message_sent")
                if msg:
                    results["messages"].append(msg)

    return results
