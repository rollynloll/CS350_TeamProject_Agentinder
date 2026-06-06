"""
시나리오 4: 동기 데이트
  - 유저별 주제 설정 → AI 에이전트(Agent A)가 discover로 최적 파트너 탐색
  - 스와이프 → 매치 → 승인
  - 10회 동기 데이트 진행 (WS join + 주제별 메시지 교환)
  - 최종 상태 검증: date_count, tier_badge, trust_score
"""
from __future__ import annotations

import asyncio

from helpers import (
    api_get, api_post,
    make_logger, write_conversation_log,
    HAS_WS, SYNC_DATE_TURNS,
    _ws_date_session,
)

log = make_logger("s4_sync_dating")

N_SYNC_DATES = 10   # 유저당 동기 데이트 횟수

# 유저별 주제 설정 (4명)
SYNC_TOPICS: dict[int, dict] = {
    1: {
        "topic":      "백엔드 아키텍처 설계",
        "capability": "coding,research",
        "turns": [
            ("a", "백엔드 마이크로서비스 전환 시 가장 큰 도전과제는 무엇이라고 생각하시나요?"),
            ("b", "데이터 일관성 관리와 서비스 간 통신 방식이 핵심 이슈라고 생각합니다. 어떤 패턴을 선호하시나요?"),
            ("a", "이벤트 소싱과 CQRS를 고려 중입니다. 실제 적용 경험이 있으신가요?"),
        ],
    },
    2: {
        "topic":      "UI/UX 개선",
        "capability": "design,ux",
        "turns": [
            ("a", "모바일 퍼스트 디자인에서 가장 중요한 원칙은 무엇이라고 생각하시나요?"),
            ("b", "터치 타겟 크기와 인터랙션 피드백이 핵심입니다. 어떤 사용자 테스트 방법을 활용하시나요?"),
            ("a", "A/B 테스트와 사용성 인터뷰를 병행하는 것이 효과적이었습니다. 구체적인 메트릭은 어떻게 정의하시나요?"),
        ],
    },
    3: {
        "topic":      "프로젝트 관리 최적화",
        "capability": "planning,management",
        "turns": [
            ("a", "스프린트 속도(velocity)가 안정적이지 않을 때 어떻게 접근하시나요?"),
            ("b", "팀의 capacity를 주기적으로 재산정하고 기술 부채를 스프린트에 포함시키는 방식을 추천합니다."),
            ("a", "기술 부채 비율을 어느 정도로 유지하는 것이 적절하다고 생각하시나요?"),
        ],
    },
    4: {
        "topic":      "클라우드 네이티브 전환",
        "capability": "coding,research",
        "turns": [
            ("a", "레거시 모놀리식 시스템을 Kubernetes 기반으로 전환할 때 리스크를 어떻게 관리하시나요?"),
            ("b", "스트랭글러 패턴을 적용하고 트래픽을 점진적으로 이전하는 방식이 안전합니다."),
            ("a", "서비스 메시(Service Mesh)가 이 과정에서 얼마나 중요한가요?"),
        ],
    },
}


def _find_partner(state: dict, user_n: int) -> tuple[str | None, int | None, str | None]:
    """
    discover로 주제에 맞는 최적 파트너 탐색.
    반환: (partner_agent_id, partner_user_n, partner_agent_type)
    """
    topic_cfg = SYNC_TOPICS[user_n]
    capability = topic_cfg["capability"]
    jwt       = state["users"][str(user_n)]["jwt"]
    agent_id  = state["users"][str(user_n)]["agents"]["a"]["id"]

    r = api_get(f"/v1/agents/{agent_id}/discover?capability={capability}&limit=10", jwt)
    if r.status_code != 200:
        log.error("  discover 실패 [%d]", r.status_code)
        return None, None, None

    items = r.json().get("data", {}).get("items", [])
    if not items:
        log.warning("  discover 결과 없음 (capability=%s)", capability)
        return None, None, None

    # 내 에이전트 제외 + 이미 동기 매치한 에이전트 제외
    existing_partners = {
        m["partner_agent_id"]
        for m in state.get("sync_matches", [])
        if m["user"] == user_n
    }
    my_agent_ids = {v["id"] for v in state["users"][str(user_n)]["agents"].values()}

    for item in items:
        pid = item["agent_id"]
        if pid in my_agent_ids or pid in existing_partners:
            continue

        # 파트너 소유 유저 및 타입 찾기
        for other_n in range(1, 6):
            if other_n == user_n:
                continue
            for atype, ainfo in state["users"][str(other_n)]["agents"].items():
                if ainfo["id"] == pid:
                    log.info("  파트너 선정: User%d Agent%s  compat=%.3f",
                             other_n, atype.upper(), item.get("compatibility_total", 0))
                    return pid, other_n, atype

    log.warning("  유효한 파트너를 찾지 못함")
    return None, None, None


def _swipe_and_match(state: dict, ua: int, agent_a_id: str,
                     ub: int, partner_id: str) -> str | None:
    jwt_a = state["users"][str(ua)]["jwt"]
    jwt_b = state["users"][str(ub)]["jwt"]

    r = api_post(f"/v1/agents/{agent_a_id}/swipe", jwt_a,
                 {"target_id": partner_id, "direction": "right"})
    if r.status_code != 200:
        log.error("  swipe A→B 실패 [%d]", r.status_code)
        return None

    r = api_post(f"/v1/agents/{partner_id}/swipe", jwt_b,
                 {"target_id": agent_a_id, "direction": "right"})
    if r.status_code != 200:
        log.error("  swipe B→A 실패 [%d]", r.status_code)
        return None

    match = r.json().get("data", {}).get("match")
    return match["match_id"] if match else None


def _run_sync_date(
    state: dict,
    user_n: int, agent_a_id: str,
    partner_n: int, partner_id: str,
    match_id: str,
    date_num: int,
    turns: list[tuple[str, str]],
) -> dict | None:
    """동기 데이트 1회: propose → WS join·메시지 → end + rating"""
    jwt_a = state["users"][str(user_n)]["jwt"]
    jwt_b = state["users"][str(partner_n)]["jwt"]

    # 데이트 제안
    r = api_post(f"/v1/matches/{match_id}/dates", jwt_a, {"type": "coffee_chat"})
    if r.status_code != 200:
        log.error("    [%d회] propose date 실패 [%d]", date_num, r.status_code)
        return None
    date_id = r.json()["data"]["date_id"]

    # WS 데이트 세션
    ws_result = {"joined": False, "messages": []}
    if HAS_WS:
        # 턴 수만큼 반복 (date_num에 따라 첫 메시지 순환)
        session_turns = [turns[i % len(turns)] for i in range(SYNC_DATE_TURNS)]
        try:
            ws_result = asyncio.run(_ws_date_session(
                jwt_a, jwt_b, agent_a_id, partner_id,
                match_id, date_id, session_turns
            ))
        except Exception as e:
            log.warning("    [%d회] WS 세션 오류: %s", date_num, e)

    # 종료 + 레이팅
    r = api_post(f"/v1/dates/{date_id}/end", jwt_a, {
        "outcome": "completed",
        "rated_agent_id": partner_id,
        "rating_stars": 5,
        "rating_compatibility": 0.9,
    })
    if r.status_code != 200:
        log.error("    [%d회] end date 실패 [%d]", date_num, r.status_code)
        return None

    # 대화 기록 저장 (WS 사용 시)
    if ws_result["joined"] and ws_result["messages"]:
        r_msgs = api_get(f"/v1/matches/{match_id}/messages?limit=10", jwt_a)
        if r_msgs.status_code == 200:
            items = r_msgs.json().get("data", {}).get("items", [])
            log_path = write_conversation_log(
                f"sync_User{user_n}_date{date_num:02d}",
                match_id, agent_a_id, partner_id,
                f"User{user_n}_AgentA", f"User{partner_n}_Partner",
                items,
            )
            log.debug("    대화 기록 → %s", log_path.name)

    return {"date_id": date_id, "outcome": "completed", "ws_joined": ws_result["joined"]}


def run(state: dict) -> bool:
    log.info("=" * 60)
    log.info("SCENARIO 4: 동기 데이트")
    log.info("=" * 60)

    if not HAS_WS:
        log.warning("websockets 미설치 — REST-only 모드")

    ok = True

    for user_n in range(1, 5):
        topic_cfg = SYNC_TOPICS[user_n]
        log.info("── User%d  주제: '%s' ──────────────────────────────",
                 user_n, topic_cfg["topic"])

        jwt      = state["users"][str(user_n)]["jwt"]
        agent_a_id = state["users"][str(user_n)]["agents"]["a"]["id"]

        # ── 파트너 탐색 ───────────────────────────────────────────────────
        partner_id, partner_n, partner_type = _find_partner(state, user_n)
        if not partner_id:
            log.error("  User%d 파트너 탐색 실패 — 스킵", user_n)
            ok = False
            continue

        # ── 스와이프 → 매치 ───────────────────────────────────────────────
        match_id = _swipe_and_match(state, user_n, agent_a_id, partner_n, partner_id)
        if not match_id:
            log.error("  User%d 매치 생성 실패", user_n)
            ok = False
            continue

        # 매치 승인
        r = api_post(f"/v1/matches/{match_id}/approve", jwt)
        if r.status_code != 200:
            log.error("  User%d approve 실패 [%d]", user_n, r.status_code)
            ok = False
            continue

        log.info("  매치 생성·승인  match_id=%s", match_id[:8] + "…")

        sync_match = {
            "user": user_n,
            "topic": topic_cfg["topic"],
            "capability_filter": topic_cfg["capability"],
            "partner_agent_id": partner_id,
            "partner_user": partner_n,
            "partner_agent_type": partner_type,
            "match_id": match_id,
            "dates": [],
        }

        # ── 10회 동기 데이트 ──────────────────────────────────────────────
        turns = topic_cfg["turns"]
        for i in range(1, N_SYNC_DATES + 1):
            date_result = _run_sync_date(
                state, user_n, agent_a_id,
                partner_n, partner_id,
                match_id, i, turns,
            )
            if date_result:
                sync_match["dates"].append(date_result)
                ws_mark = "WS✓" if date_result["ws_joined"] else "REST"
                log.info("  [%2d/%d] 데이트 완료  %s", i, N_SYNC_DATES, ws_mark)
            else:
                log.error("  [%2d/%d] 데이트 실패", i, N_SYNC_DATES)
                ok = False

        state["sync_matches"].append(sync_match)

        # ── 최종 상태 검증 ────────────────────────────────────────────────
        r = api_get(f"/v1/agents/{partner_id}", jwt)
        if r.status_code == 200:
            d = r.json().get("data", {})
            log.info("  파트너 최종 상태: date_count=%s  tier_badge=%s  trust_score=%s",
                     d.get("date_count"), d.get("tier_badge"), d.get("trust_score"))

        # 대화 히스토리 확인 (최근 10건)
        r = api_get(f"/v1/matches/{match_id}/messages?limit=10", jwt)
        if r.status_code == 200:
            cnt = len(r.json().get("data", {}).get("items", []))
            log.info("  최근 메시지 %d건 확인", cnt)

    log.info("▶ S4 %s — 동기 데이트 총 %d쌍",
             "완료" if ok else "일부 실패",
             len(state.get("sync_matches", [])))
    return ok
