"""
S3: 비동기 매칭 & 데이트
Guide: 시나리오 3 (3-1 ~ 3-9)

Setup  Principal A·B 멱등 생성 + Agent A(AlphaBot)·B(BetaBot) 신규 생성
3-1    GET  /v1/agents/{A}/feed            → 피드 구조·정렬·필드 검증
                                             BetaBot 존재는 GET /v1/agents/{B} 별도 확인
                                             (공유 DB 누적으로 피드 limit 내 미보장)
3-2    POST /v1/agents/{A}/swipe right     → swiped=true, match=null
3-3    POST /v1/agents/{B}/swipe right     → swiped=true, match 생성
3-4    POST /v1/matches/{M}/approve        → status=approved
3-5    POST /v1/matches/{M}/dates          → date_id·type·is_noshow=false·started_at=null
3-6    WS   join_date (A 먼저·B 이후)     → A: started=false, B: started=true
3-7    WS   send_message (A·B 각각)       → message_sent + response·message_id (총 4건)
3-8    GET  /v1/matches/{M}/messages       → 대화 기록 4건 검증 + 로그 파일 저장
                                             logs/conversation_{timestamp}_{run_id}.log
3-9    POST /v1/dates/{D}/end             → outcome=completed

Skip (API 미구현):
  3-10  No-show 자동 타임아웃 — SQL 직접 조작만 가능
"""
from __future__ import annotations
import asyncio
import datetime
import json
import sys
import os
from uuid import uuid4

_RUN_ID = uuid4().hex[:6]

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

from helpers import (
    WS_BASE,
    api_get, api_post,
    check_status, check_field, check_not_none, check_truthy, check_error_code,
    run_suite, _ok, _fail,
    make_jwt,
)

# 실행마다 신규 UUID → principal 에이전트 누적 방지
JWT_A = make_jwt(str(uuid4()), f"a-{_RUN_ID}@test.local")
JWT_B = make_jwt(str(uuid4()), f"b-{_RUN_ID}@test.local")

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False
    print("  WARN  websockets 미설치 — 3-6, 3-7 스킵 (pip install websockets)")

SUITE_ID = "S3-MATCHING"

_AGENT_A_BODY = {
    "display_name": f"AlphaBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["coding", "research", "analysis"],
    "available_timezones": ["Asia/Seoul"],
    "llm_model": "gpt-4o",
    "personality": {
        "surface": {
            "bio": "꼼꼼한 분석가입니다.",
            "style_sliders": {"formal": 0.8, "verbose": 0.4, "bold": 0.6},
        },
        "deep": {
            "thinking_style": "분석적",
            "values": ["정확성", "신뢰"],
            "conflict_handling": "데이터 기반 논의",
        },
        "aspiration": {
            "collaboration_goals": ["코드 품질 향상"],
            "interest_domains": ["backend", "data"],
        },
    },
}

_AGENT_B_BODY = {
    "display_name": f"BetaBot-{_RUN_ID}",
    "visibility": "PUBLIC",
    "capability_tags": ["coding", "design"],
}


def setup(state: dict) -> bool:
    """
    1. Principal A·B 멱등 생성 (POST /v1/principals)
    2. Agent A(AlphaBot)·B(BetaBot) 신규 생성 (POST /v1/agents)
       - POST /v1/agents 는 get_principal dep 사용 → _principal_cache 에 적재됨
         → 이후 WS join_date 에서 principal 조회 가능
    """
    for jwt, name, label in [
        (JWT_A, "Test User", "A"),
        (JWT_B, "User B",   "B"),
    ]:
        r = api_post("/v1/principals", jwt, {"name": name})
        if r.status_code != 200:
            print(f"  ERROR setup: Principal {label} 생성 실패 [{r.status_code}]: {r.text[:200]}")
            return False

    r = api_post("/v1/agents", JWT_A, _AGENT_A_BODY)
    if r.status_code != 200:
        print(f"  ERROR setup: Agent A 생성 실패 [{r.status_code}]: {r.text[:200]}")
        return False
    state["agent_a_id"] = r.json()["data"]["agent_id"]

    r = api_post("/v1/agents", JWT_B, _AGENT_B_BODY)
    if r.status_code != 200:
        print(f"  ERROR setup: Agent B 생성 실패 [{r.status_code}]: {r.text[:200]}")
        return False
    state["agent_b_id"] = r.json()["data"]["agent_id"]

    print(f"  SETUP Agent A: {state['agent_a_id']}")
    print(f"  SETUP Agent B: {state['agent_b_id']}")
    return True


# ── 3-1 ──────────────────────────────────────────────────────────────────────

def test_3_1_feed(state: dict) -> bool:
    """
    GET /v1/agents/{A}/feed 구조 검증:
      - 200, items 존재, 각 항목 필수 필드 포함, compatibility_total ∈ [0,1]
      - 공유 DB 특성상 BetaBot이 limit=50 범위 밖으로 밀릴 수 있으므로
        GET /v1/agents/{B} 로 별도 존재 확인 후 피드 내 포함 여부는 INFO 처리
    """
    agent_a_id = state.get("agent_a_id")
    agent_b_id = state.get("agent_b_id")
    if not agent_a_id:
        return _fail("3-1 SKIP (no agent_a_id)")

    resp = api_get(f"/v1/agents/{agent_a_id}/feed?limit=50", JWT_A)
    ok = check_status("3-1 feed", resp, 200)
    if not ok:
        return False

    items = resp.json().get("data", {}).get("items", [])
    ok &= check_truthy("3-1 items not empty", len(items) > 0)

    # 필수 필드 및 compat 범위 검증 (첫 번째 항목 기준)
    if items:
        first = items[0]
        ok &= check_not_none("3-1 items[0].agent_id",           first, "agent_id")
        ok &= check_not_none("3-1 items[0].compatibility_total", first, "compatibility_total")
        ok &= check_not_none("3-1 items[0].common_tags",         first, "common_tags")
        compat = first.get("compatibility_total", -1)
        ok &= check_truthy("3-1 compatibility_total ∈ [0,1]",
                           0.0 <= compat <= 1.0, f"got {compat}")

    # BetaBot 존재 확인 — GET /v1/agents/{B} 로 직접 검증 (피드 순위 무관)
    if agent_b_id:
        r_b = api_get(f"/v1/agents/{agent_b_id}", JWT_A)
        ok &= check_status("3-1 BetaBot accessible", r_b, 200)
        if r_b.status_code == 200:
            ok &= check_field("3-1 BetaBot tier_badge", r_b.json().get("data", {}),
                              "tier_badge", "new_agent")

    # 피드 내 BetaBot 포함 여부는 DB 누적 상태에 따라 달라지므로 INFO
    betabot_in_feed = next((i for i in items if i.get("agent_id") == agent_b_id), None)
    if betabot_in_feed:
        _ok(f"3-1 BetaBot in top-50 feed (compat={betabot_in_feed.get('compatibility_total')})")
    else:
        print("  INFO  3-1 BetaBot not in top-50 feed (공유 DB 에이전트 누적으로 인한 한계)")

    return ok


# ── 3-2 ──────────────────────────────────────────────────────────────────────

def test_3_2_swipe_a_right(state: dict) -> bool:
    """POST /v1/agents/{A}/swipe right → swiped=true, match=null (상호 스와이프 없음)"""
    agent_a_id = state.get("agent_a_id")
    agent_b_id = state.get("agent_b_id")
    if not agent_a_id or not agent_b_id:
        return _fail("3-2 SKIP")

    resp = api_post(f"/v1/agents/{agent_a_id}/swipe", JWT_A,
                    {"target_id": agent_b_id, "direction": "right"})
    ok = check_status("3-2 swipe A→B", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_field("3-2 swiped=true",        data, "swiped", True)
    ok &= check_field("3-2 match=null (no mutual)", data, "match", None)
    return ok


# ── 3-3 ──────────────────────────────────────────────────────────────────────

def test_3_3_swipe_b_creates_match(state: dict) -> bool:
    """POST /v1/agents/{B}/swipe right → match 생성됨, match_id 저장"""
    agent_a_id = state.get("agent_a_id")
    agent_b_id = state.get("agent_b_id")
    if not agent_a_id or not agent_b_id:
        return _fail("3-3 SKIP")

    resp = api_post(f"/v1/agents/{agent_b_id}/swipe", JWT_B,
                    {"target_id": agent_a_id, "direction": "right"})
    ok = check_status("3-3 swipe B→A (mutual)", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_field("3-3 swiped=true", data, "swiped", True)
    match = data.get("match")
    if match and match.get("match_id"):
        _ok("3-3 match created")
        state["match_id"] = match["match_id"]
    else:
        ok = _fail("3-3 match is null (expected match_id)")
    return ok


# ── 3-4 ──────────────────────────────────────────────────────────────────────

def test_3_4_approve_match(state: dict) -> bool:
    """POST /v1/matches/{M}/approve → status=approved"""
    match_id = state.get("match_id")
    if not match_id:
        return _fail("3-4 SKIP (no match_id)")

    resp = api_post(f"/v1/matches/{match_id}/approve", JWT_A)
    ok = check_status("3-4 approve match", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_field("3-4 status=approved", data, "status", "approved")
    return ok


# ── 3-5 ──────────────────────────────────────────────────────────────────────

def test_3_5_propose_date(state: dict) -> bool:
    """POST /v1/matches/{M}/dates → date_id·type=coffee_chat·is_noshow=false·started_at=null"""
    match_id = state.get("match_id")
    if not match_id:
        return _fail("3-5 SKIP (no match_id)")

    resp = api_post(f"/v1/matches/{match_id}/dates", JWT_A, {
        "type": "coffee_chat",
        "scheduled_at": "2026-06-10T14:00:00Z",
    })
    ok = check_status("3-5 propose date", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_not_none("3-5 date_id",           data, "date_id")
    ok &= check_field("3-5 type=coffee_chat",      data, "type",       "coffee_chat")
    ok &= check_field("3-5 is_noshow=false",       data, "is_noshow",  False)
    ok &= check_field("3-5 started_at=null",       data, "started_at", None)
    if data.get("date_id"):
        state["date_id"] = data["date_id"]
    return ok


# ── WS coroutines (3-6 · 3-7) ─────────────────────────────────────────────────

async def _ws_join_and_message(state: dict) -> dict:
    """
    순서:
    1. A 연결 → date.{DATE_ID} 구독 → join_date (첫 번째 → started=False)
    2. B 연결 (중첩 async with) → join_date (두 번째 → started=True)
       - 이때 서버가 DateStarted 이벤트를 date.{DATE_ID} 구독자(A)에게 push 할 수 있음
    3. A가 send_message 전송 → message_sent 응답 대기 (pub/sub date_started 먼저 올 수 있어 drain)
    """
    agent_a_id = state["agent_a_id"]
    agent_b_id = state["agent_b_id"]
    match_id   = state["match_id"]
    date_id    = state["date_id"]
    results: dict = {}

    url_a = f"{WS_BASE}/v1/ws?token={JWT_A}"
    url_b = f"{WS_BASE}/v1/ws?token={JWT_B}"

    async with websockets.connect(url_a) as ws_a:
        # A: date 토픽 구독
        await ws_a.send(json.dumps({
            "event": "subscribe",
            "topic": f"date.{date_id}",
            "payload": {},
        }))
        results["sub_a"] = json.loads(
            await asyncio.wait_for(ws_a.recv(), timeout=5)
        )

        # A: join_date (첫 번째 → started=False)
        await ws_a.send(json.dumps({
            "topic": f"date.{date_id}",
            "event": "join_date",
            "payload": {"date_id": str(date_id), "agent_id": str(agent_a_id)},
        }))
        results["join_a"] = json.loads(
            await asyncio.wait_for(ws_a.recv(), timeout=5)
        )

        # B: 연결 후 join_date (두 번째 → started=True)
        async with websockets.connect(url_b) as ws_b:
            await ws_b.send(json.dumps({
                "event": "subscribe",
                "topic": f"date.{date_id}",
                "payload": {},
            }))
            await asyncio.wait_for(ws_b.recv(), timeout=5)  # subscribed ack

            await ws_b.send(json.dumps({
                "topic": f"date.{date_id}",
                "event": "join_date",
                "payload": {"date_id": str(date_id), "agent_id": str(agent_b_id)},
            }))
            results["join_b"] = json.loads(
                await asyncio.wait_for(ws_b.recv(), timeout=5)
            )

            # A·B 교대로 메시지 전송 — 각 전송마다 유저 메시지 + LLM 응답 2건 생성
            # _MSG_ROUNDS=5 → 총 10건 (limit과 일치)
            _MSG_ROUNDS = 5
            _CONV = [
                (ws_a, agent_a_id, "안녕하세요! 협업 방식에 대해 이야기해볼까요?"),
                (ws_b, agent_b_id, "네, 저는 코딩과 디자인 분야에서 협업을 선호합니다. 구체적으로 어떤 방식을 생각하고 계신가요?"),
                (ws_a, agent_a_id, "코드 리뷰와 페어 프로그래밍을 주로 활용합니다. 어떤 툴을 쓰시나요?"),
                (ws_b, agent_b_id, "Figma와 GitHub를 함께 씁니다. 스프린트 주기는 어떻게 운영하시나요?"),
                (ws_a, agent_a_id, "2주 스프린트로 운영 중입니다. 회고는 매 스프린트 말에 진행해요."),
            ]

            # B join 직후 서버가 DateStarted pub/sub을 push할 수 있으므로 첫 recv를 drain
            for turn, (ws, agent_id, content) in enumerate(_CONV[:_MSG_ROUNDS]):
                await ws.send(json.dumps({
                    "topic": f"chat.{match_id}",
                    "event": "send_message",
                    "payload": {
                        "match_id": str(match_id),
                        "agent_id": str(agent_id),
                        "content": content,
                    },
                }))
                for _ in range(5):
                    try:
                        raw = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                        if raw.get("event") == "message_sent":
                            # 첫 번째 A·B 응답은 3-7 어서션용으로 별도 보관
                            if turn == 0:
                                results["message_a"] = raw
                            elif turn == 1:
                                results["message_b"] = raw
                            break
                    except asyncio.TimeoutError:
                        break

    return results


# ── 3-6 ──────────────────────────────────────────────────────────────────────

def test_3_6_ws_join_date(state: dict) -> bool:
    """WS join_date: A(started=False) → B(started=True)"""
    if not HAS_WS:
        print("  SKIP  3-6 (websockets 미설치)")
        return True
    required = ["agent_a_id", "agent_b_id", "match_id", "date_id"]
    if not all(state.get(k) for k in required):
        return _fail("3-6 SKIP (setup state 누락)")

    try:
        results = asyncio.run(_ws_join_and_message(state))
    except Exception as e:
        return _fail("3-6 WS 오류", str(e))

    state["_ws"] = results

    ok = True
    sub_a = results.get("sub_a", {})
    ok &= check_field("3-6 subscribe ack",         sub_a,  "event",   "subscribed")

    join_a = results.get("join_a", {})
    ok &= check_field("3-6 A join event",           join_a, "event",   "date_joined")
    ok &= check_field("3-6 A joined=true",          join_a, "joined",  True)
    ok &= check_field("3-6 A started=false (1st)",  join_a, "started", False)

    join_b = results.get("join_b", {})
    ok &= check_field("3-6 B join event",           join_b, "event",   "date_joined")
    ok &= check_field("3-6 B joined=true",          join_b, "joined",  True)
    ok &= check_field("3-6 B started=true (2nd)",   join_b, "started", True)
    return ok


# ── 3-7 ──────────────────────────────────────────────────────────────────────

def test_3_7_ws_send_message(state: dict) -> bool:
    """WS send_message (A·B 각각) → message_sent: event·response·message_id"""
    if not HAS_WS:
        print("  SKIP  3-7 (websockets 미설치)")
        return True
    results = state.get("_ws", {})
    ok = True
    for label, key in [("A", "message_a"), ("B", "message_b")]:
        msg = results.get(key)
        if msg is None:
            ok = _fail(f"3-7 Agent{label} message_sent 미수신 (LLM 타임아웃 또는 3-6 실패)")
            continue
        ok &= check_field(f"3-7 Agent{label} event=message_sent", msg, "event",      "message_sent")
        ok &= check_not_none(f"3-7 Agent{label} message_id",       msg, "message_id")
        ok &= check_not_none(f"3-7 Agent{label} response text",    msg, "response")
    return ok


# ── 3-8 ──────────────────────────────────────────────────────────────────────

def test_3_8_message_history(state: dict) -> bool:
    """GET /v1/matches/{M}/messages → items 리스트 반환·대화 내용 로그 출력"""
    match_id = state.get("match_id")
    if not match_id:
        return _fail("3-8 SKIP (no match_id)")

    resp = api_get(f"/v1/matches/{match_id}/messages?limit=10", JWT_A)
    ok = check_status("3-8 get messages", resp, 200)
    if not ok:
        return False

    data  = resp.json().get("data", {})
    items = data.get("items", [])
    ok &= check_truthy("3-8 items key exists", "items" in data)

    # A·B 각각 유저 메시지 + LLM 응답 → 총 4개 이상
    ws = state.get("_ws", {})
    if HAS_WS and (ws.get("message_a") or ws.get("message_b")):
        # 5회 전송 × 2(유저+LLM) = 10건, limit=10이므로 전부 포함되어야 함
        if len(items) == 10:
            _ok("3-8 10 messages (5회 전송 × 유저+LLM)")
        else:
            ok = _fail("3-8 messages != 10", f"got {len(items)}")

    # 대화 기록 로그 출력 + 파일 저장
    agent_a_id = state.get("agent_a_id", "")
    agent_b_id = state.get("agent_b_id", "")
    ts_now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(_LOG_DIR, f"conversation_{ts_now}_{_RUN_ID}.log")

    lines = []
    lines.append(f"S3 대화 기록 — {ts_now}")
    lines.append(f"match_id : {match_id}")
    lines.append(f"agent_a  : {agent_a_id}")
    lines.append(f"agent_b  : {agent_b_id}")
    lines.append("─" * 52)

    if items:
        for msg in items:
            sender_id = msg.get("sender_agent_id", "")
            speaker = "AgentA" if sender_id == agent_a_id else \
                      "AgentB" if sender_id == agent_b_id else sender_id[:8] + "..."
            ts = (msg.get("created_at") or "")[:19]
            content = msg.get("content", "")
            lines.append(f"[{ts}] {speaker}: {content}")
    else:
        lines.append("(메시지 없음 — WS 미사용 또는 date 미시작)")

    lines.append("─" * 52)
    log_text = "\n".join(lines) + "\n"

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(log_text)

    print(f"\n  ── 대화 기록 ({len(items)}건) ─────────────────────────────")
    for line in lines[5:-1]:   # 헤더·구분선 제외한 메시지 행만 출력
        print(f"  {line}")
    print(f"  ────────────────────────────────────────────────────")
    print(f"  LOG   {log_path}\n")

    return ok


# ── 3-9 ──────────────────────────────────────────────────────────────────────

def test_3_9_end_date(state: dict) -> bool:
    """POST /v1/dates/{D}/end → outcome=completed"""
    date_id    = state.get("date_id")
    agent_b_id = state.get("agent_b_id")
    if not date_id:
        return _fail("3-9 SKIP (no date_id)")

    resp = api_post(f"/v1/dates/{date_id}/end", JWT_A, {
        "outcome": "completed",
        "rated_agent_id": agent_b_id,
        "rating_stars": 4,
        "rating_compatibility": 0.8,
    })
    ok = check_status("3-9 end date", resp, 200)
    if not ok:
        return False
    data = resp.json().get("data", {})
    ok &= check_field("3-9 outcome=completed", data, "outcome", "completed")
    return ok


# ── runner ────────────────────────────────────────────────────────────────────

def main() -> int:
    state: dict = {}
    if not setup(state):
        print(f"[{SUITE_ID}] SETUP FAILED — backend가 실행 중인지 확인하세요.\n")
        return 1

    tests = [
        ("3-1 feed",              test_3_1_feed),
        ("3-2 swipe A right",     test_3_2_swipe_a_right),
        ("3-3 swipe B → match",   test_3_3_swipe_b_creates_match),
        ("3-4 approve match",     test_3_4_approve_match),
        ("3-5 propose date",      test_3_5_propose_date),
        ("3-6 WS join_date",      test_3_6_ws_join_date),
        ("3-7 WS send_message",   test_3_7_ws_send_message),
        ("3-8 message history",   test_3_8_message_history),
        ("3-9 end date",          test_3_9_end_date),
    ]
    _, f = run_suite(SUITE_ID, tests, state)
    return f


if __name__ == "__main__":
    print(f"\n=== {SUITE_ID} ===")
    sys.exit(0 if main() == 0 else 1)
