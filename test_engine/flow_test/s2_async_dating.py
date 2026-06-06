"""
시나리오 2: 비동기 데이트
  - PUBLIC async 에이전트: 4명 × 2(a·b) = 8개, cross-user 쌍 = 24

  실행 모드 (run() mode 파라미터):
    "single"  — 임의의 쌍 1개 선택, 데이트 1회               (총  1 데이트)
    "all_n"   — 전체 24쌍 × n회 (n=run()의 n 파라미터)       (총 24n 데이트)
    "all_10"  — 전체 24쌍 × 10회 (기본 풀 모드)              (총 240 데이트)

  각 데이트: 상호 스와이프(최초 1회) → 승인 → propose → WS 5 turns(대화 10건) → end+rating
  WS 미설치 시 REST-only 모드
"""
from __future__ import annotations

import asyncio
from itertools import combinations

from helpers import (
    api_get, api_post,
    make_logger, write_conversation_log,
    HAS_WS, ASYNC_DATE_TURNS,
    _ws_date_session,
)

log = make_logger("s2_async_dating")

# ── 에이전트 타입별 대화 메시지 (발신 타입 기준) ─────────────────────────────
# 5 turns: A→B→A→B→A (sends 3+2) — ASYNC_DATE_TURNS=5 과 동기화
_ROLE_MSGS: dict[str, list[str]] = {
    "a": [
        "코드 품질 향상과 효율적인 시스템 설계에 대해 어떻게 생각하시나요?",
        "최근 관심 있는 기술 트렌드나 아키텍처 패턴이 있다면 공유해 주세요.",
        "성능 최적화 경험 중 가장 인상 깊었던 사례를 알려주실 수 있나요?",
    ],
    "b": [
        "사용자 경험 개선을 위해 가장 중요하게 여기는 디자인 원칙은 무엇인가요?",
        "디자인과 개발 협업을 효율화한 성공적인 경험이 있으신가요?",
    ],
    "c": [
        "팀 생산성을 높이기 위해 어떤 방법을 활용하고 계신가요?",
        "프로젝트 관리 과정에서 가장 어려운 부분은 무엇이었나요?",
    ],
}


def _build_turns(ta: str, tb: str) -> list[tuple[str, str]]:
    """
    ASYNC_DATE_TURNS(=5) 수만큼 (sender, content) 튜플 생성.
    순서: a→b→a→b→a (3회 a, 2회 b)
    각 메시지는 발신 에이전트 타입의 풀에서 순환.
    """
    msgs_a = _ROLE_MSGS.get(ta, _ROLE_MSGS["a"])
    msgs_b = _ROLE_MSGS.get(tb, _ROLE_MSGS["b"])
    pattern = ["a", "b", "a", "b", "a"]   # 5 turns
    idx_a = idx_b = 0
    turns = []
    for sender in pattern[:ASYNC_DATE_TURNS]:
        if sender == "a":
            turns.append(("a", msgs_a[idx_a % len(msgs_a)]))
            idx_a += 1
        else:
            turns.append(("b", msgs_b[idx_b % len(msgs_b)]))
            idx_b += 1
    return turns


def _build_match_plan(state: dict) -> list[dict]:
    """
    모든 cross-user 에이전트 쌍 90개를 반환.
    각 항목: {ua, ta, ub, tb, agent_a_id, agent_b_id, jwt_a, jwt_b}
    """
    # PUBLIC 에이전트만 (a·b) — d(HIDDEN)는 비동기 불허
    all_agents = [
        (n, t)
        for n in range(1, 5)   # 4명
        for t in ["a", "b"]    # PUBLIC 타입만
    ]

    plan = []
    for (ua, ta), (ub, tb) in combinations(all_agents, 2):
        if ua == ub:
            continue  # 동일 유저 내 쌍 제외
        plan.append({
            "ua": ua, "ta": ta,
            "ub": ub, "tb": tb,
            "agent_a_id": state["users"][str(ua)]["agents"][ta]["id"],
            "agent_b_id": state["users"][str(ub)]["agents"][tb]["id"],
            "jwt_a": state["users"][str(ua)]["jwt"],
            "jwt_b": state["users"][str(ub)]["jwt"],
        })
    return plan  # 총 90개


def _swipe_and_match(p: dict) -> str | None:
    """상호 스와이프 → match_id 반환. 실패 시 None."""
    r = api_post(f"/v1/agents/{p['agent_a_id']}/swipe", p["jwt_a"],
                 {"target_id": p["agent_b_id"], "direction": "right"})
    if r.status_code != 200:
        return None

    r = api_post(f"/v1/agents/{p['agent_b_id']}/swipe", p["jwt_b"],
                 {"target_id": p["agent_a_id"], "direction": "right"})
    if r.status_code != 200:
        return None

    match = r.json().get("data", {}).get("match")
    return match["match_id"] if match else None


def _run_date(p: dict, match_id: str) -> dict | None:
    """데이트 1회: propose → WS(5 turns = 10 messages) → end + rating."""
    # 데이트 제안
    r = api_post(f"/v1/matches/{match_id}/dates", p["jwt_a"],
                 {"type": "coffee_chat"})
    if r.status_code != 200:
        log.error("    propose date 실패 [%d]: %s", r.status_code, r.text[:100])
        return None
    date_id = r.json()["data"]["date_id"]

    # WS 데이트 세션 (5 turns → 10 messages)
    ws_result = {"joined": False, "messages": []}
    if HAS_WS:
        turns = _build_turns(p["ta"], p["tb"])
        try:
            ws_result = asyncio.run(_ws_date_session(
                p["jwt_a"], p["jwt_b"],
                p["agent_a_id"], p["agent_b_id"],
                match_id, date_id, turns,
            ))
        except Exception as e:
            log.warning("    WS 세션 오류: %s", e)

    # 종료 + 레이팅
    r = api_post(f"/v1/dates/{date_id}/end", p["jwt_a"], {
        "outcome": "completed",
        "rated_agent_id": p["agent_b_id"],
        "rating_stars": 4,
        "rating_compatibility": 0.8,
    })
    if r.status_code != 200:
        log.error("    end date 실패 [%d]: %s", r.status_code, r.text[:100])
        return None

    # 대화 기록 저장
    if ws_result["joined"]:
        r_msgs = api_get(f"/v1/matches/{match_id}/messages?limit=10", p["jwt_a"])
        if r_msgs.status_code == 200:
            items = r_msgs.json().get("data", {}).get("items", [])
            label_a = f"User{p['ua']}_Agent{p['ta'].upper()}"
            label_b = f"User{p['ub']}_Agent{p['tb'].upper()}"
            write_conversation_log(
                f"async_U{p['ua']}A{p['ta']}_U{p['ub']}A{p['tb']}",
                match_id, p["agent_a_id"], p["agent_b_id"],
                label_a, label_b, items,
            )

    return {
        "date_id":   date_id,
        "outcome":   "completed",
        "rating":    4,
        "ws_joined": ws_result["joined"],
        "msg_count": len(ws_result["messages"]),
    }


def run(state: dict, mode: str = "all_10", n: int = 1) -> bool:
    """
    mode:
      "single"  — 임의의 쌍 1개, 데이트 1회
      "all_n"   — 전체 24쌍 × n회  (n 파라미터 사용)
      "all_10"  — 전체 24쌍 × 10회 (기본 풀 모드)
    """
    import random

    MODE_LABELS = {
        "single": "단일 쌍 1회",
        "all_n":  f"전체 24쌍 × {n}회",
        "all_10": "전체 24쌍 × 10회",
    }
    n_dates = {"single": 1, "all_n": n, "all_10": 10}.get(mode, 10)

    log.info("=" * 60)
    log.info("SCENARIO 2: 비동기 데이트  [모드: %s — %s]",
             mode, MODE_LABELS.get(mode, mode))
    log.info("=" * 60)
    log.info("대화: %d turns × 2 = %d건 고정 / 쌍당 데이트: %d회",
             ASYNC_DATE_TURNS, ASYNC_DATE_TURNS * 2, n_dates)

    if not HAS_WS:
        log.warning("websockets 미설치 — REST-only 모드")

    full_plan = _build_match_plan(state)   # 24쌍

    # 모드별 실행 계획
    if mode == "single":
        plan = [random.choice(full_plan)]
        total_pairs = 1
    else:
        plan = full_plan
        total_pairs = len(plan)

    total_expected = total_pairs * n_dates
    log.info("실행 계획: %d쌍 × %d회 = 총 %d 데이트",
             total_pairs, n_dates, total_expected)

    ok        = True
    match_cnt = 0
    date_cnt  = 0
    fail_cnt  = 0
    ws_cnt    = 0

    for idx, p in enumerate(plan, 1):
        pair_label = (f"User{p['ua']}_Agent{p['ta'].upper()}"
                      f" ↔ User{p['ub']}_Agent{p['tb'].upper()}")
        log.info("[쌍 %02d/%02d] %s", idx, total_pairs, pair_label)

        # 스와이프 → 매치 생성 (쌍당 1회)
        match_id = _swipe_and_match(p)
        if not match_id:
            log.error("  스와이프/매치 실패 — 스킵")
            fail_cnt += 1
            ok = False
            continue

        r = api_post(f"/v1/matches/{match_id}/approve", p["jwt_a"])
        if r.status_code != 200:
            log.error("  approve 실패 [%d] — 스킵", r.status_code)
            fail_cnt += 1
            ok = False
            continue

        match_cnt += 1
        match_dates: list[dict] = []

        # 동일 매치에서 n_dates 회 데이트
        for d in range(1, n_dates + 1):
            date_result = _run_date(p, match_id)
            if date_result:
                date_cnt += 1
                if date_result["ws_joined"]:
                    ws_cnt += 1
                match_dates.append(date_result)
                ws_mark = (f"WS✓({date_result['msg_count']}건)"
                           if date_result["ws_joined"] else "REST")
                log.info("  [데이트 %02d/%02d] match=%s  %s",
                         d, n_dates, match_id[:8] + "…", ws_mark)
            else:
                log.error("  [데이트 %02d/%02d] 실패", d, n_dates)
                fail_cnt += 1
                ok = False

        state["async_matches"].append({
            "user_a": p["ua"], "agent_a_type": p["ta"],
            "user_b": p["ub"], "agent_b_type": p["tb"],
            "match_id": match_id,
            "dates": match_dates,
        })

    # 유저별 최종 상태
    log.info("▶ 유저별 trust_score·date_count 확인")
    for n in range(1, 5):
        jwt        = state["users"][str(n)]["jwt"]
        agent_a_id = state["users"][str(n)]["agents"]["a"]["id"]
        r = api_get(f"/v1/agents/{agent_a_id}", jwt)
        if r.status_code == 200:
            d = r.json().get("data", {})
            log.info("  User%d AgentA: date_count=%-3s  trust_score=%s  tier=%s",
                     n, d.get("date_count"), d.get("trust_score"), d.get("tier_badge"))

    log.info("▶ S2 %s — 매치: %d/24  데이트: %d  WS: %d  실패: %d",
             "완료" if ok else "일부 실패",
             match_cnt, date_cnt, ws_cnt, fail_cnt)
    return ok
