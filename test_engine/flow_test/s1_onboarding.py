"""
시나리오 1: 온보딩
  - 유저 5명 계정 생성 (POST /v1/principals)
  - 유저별 에이전트 4개 생성 (agent_profiles/user_N/agent_{a,b,c,d}.json)
  - 온보딩 검증: agent 목록, 신규 에이전트 초기 상태, Agent D 피드 미노출
"""
from __future__ import annotations

from helpers import (
    api_get, api_post,
    load_profile, new_user_credentials,
    make_logger, save_state, empty_state, load_state,
    reset_principals, collect_principal_ids,
    HAS_WS,
)

log = make_logger("s1_onboarding")

N_USERS      = 4
AGENT_TYPES  = ["a", "b", "d"]   # a·b = PUBLIC, d = HIDDEN


def run(state: dict) -> bool:
    log.info("=" * 60)
    log.info("SCENARIO 1: 온보딩")
    log.info("=" * 60)

    if not HAS_WS:
        log.warning("websockets 미설치 — S2·S4 WS 데이트 세션 불가 (pip install websockets)")

    # ── 기존 데이터 리셋 ───────────────────────────────────────────────────
    # flow_state.json 에 이전 실행의 principal_id 가 있으면 DB에서 CASCADE 삭제 후 재시작
    prev_state    = load_state()
    prev_pids     = collect_principal_ids(prev_state)
    if prev_pids:
        log.info("▶ 기존 데이터 감지 (%d명) — DB 리셋 후 재생성", len(prev_pids))
        if not reset_principals(prev_pids, log):
            log.error("DB 리셋 실패 — 중단")
            return False
        # state 초기화 (이후 새 데이터로 채워짐)
        state.clear()
        state.update({"users": {}, "async_matches": [], "sync_matches": []})
    else:
        log.info("▶ 기존 데이터 없음 — 새로 생성")

    ok = True

    # ── 1-1. 유저 계정 생성 ────────────────────────────────────────────────
    log.info("▶ 1-1. 유저 계정 생성 (%d명)", N_USERS)

    for n in range(1, N_USERS + 1):
        pid, email, jwt = new_user_credentials(n)

        r = api_post("/v1/principals", jwt, {"name": f"FlowUser{n}"})
        if r.status_code != 200:
            log.error("  User%d principal 생성 실패 [%d]: %s", n, r.status_code, r.text[:200])
            return False

        state["users"][str(n)] = {
            "jwt":          jwt,
            "principal_id": pid,
            "email":        email,
            "agents":       {},
        }
        log.info("  User%d  principal_id=%s  email=%s", n, pid[:8] + "…", email)

    # ── 1-2. 에이전트 생성 ────────────────────────────────────────────────
    log.info("▶ 1-2. 에이전트 생성 (유저당 %d개 × %d명 = 총 %d개)",
             len(AGENT_TYPES), N_USERS, len(AGENT_TYPES) * N_USERS)

    for n in range(1, N_USERS + 1):
        jwt = state["users"][str(n)]["jwt"]

        for atype in AGENT_TYPES:
            profile = load_profile(n, atype)
            r = api_post("/v1/agents", jwt, profile)

            if r.status_code != 200:
                log.error("  User%d Agent%s 생성 실패 [%d]: %s",
                          n, atype.upper(), r.status_code, r.text[:200])
                ok = False
                continue

            data = r.json().get("data", {})
            state["users"][str(n)]["agents"][atype] = {
                "id":      data.get("agent_id", ""),
                "api_key": data.get("api_key", ""),  # 이 응답에서만 노출
            }
            vis = profile.get("visibility", "?")
            log.info("  User%d Agent%s  id=%s  visibility=%s",
                     n, atype.upper(), data.get("agent_id", "?")[:8] + "…", vis)

    # ── 1-3. 온보딩 검증 ─────────────────────────────────────────────────
    log.info("▶ 1-3. 온보딩 검증")

    for n in range(1, N_USERS + 1):
        jwt     = state["users"][str(n)]["jwt"]
        agents  = state["users"][str(n)]["agents"]

        # 에이전트 목록 조회
        r = api_get("/v1/agents", jwt)
        if r.status_code != 200:
            log.error("  User%d GET /v1/agents 실패 [%d]", n, r.status_code)
            ok = False
            continue
        count = len(r.json().get("data", []))
        if count == len(AGENT_TYPES):
            log.info("  User%d 에이전트 %d개 확인 ✓", n, count)
        else:
            log.error("  User%d 에이전트 수 불일치: %d (expected %d)", n, count, len(AGENT_TYPES))
            ok = False

        # Agent A 초기 상태 검증
        agent_a_id = agents.get("a", {}).get("id")
        if agent_a_id:
            r = api_get(f"/v1/agents/{agent_a_id}", jwt)
            if r.status_code == 200:
                d = r.json().get("data", {})
                assert_ok = (
                    d.get("tier_badge") == "new_agent"
                    and d.get("trust_score") is None
                    and d.get("date_count") == 0
                )
                if assert_ok:
                    log.info("  User%d AgentA 초기 상태 (new_agent, trust=null, date_count=0) ✓", n)
                else:
                    log.error("  User%d AgentA 초기 상태 불일치: %s", n, d)
                    ok = False

        # Agent D (HIDDEN) 피드 미노출 확인
        agent_d_id = agents.get("d", {}).get("id")
        if agent_a_id and agent_d_id:
            r = api_get(f"/v1/agents/{agent_a_id}/feed?limit=50", jwt)
            if r.status_code == 200:
                items = r.json().get("data", {}).get("items", [])
                ids   = {i.get("agent_id") for i in items}
                if agent_d_id not in ids:
                    log.info("  User%d AgentD (HIDDEN) 피드 미노출 ✓", n)
                else:
                    log.error("  User%d AgentD가 피드에 노출됨 (visibility=HIDDEN 위반)", n)
                    ok = False

    status = "완료" if ok else "일부 실패"
    log.info("▶ S1 %s — Users: %d, Agents: %d", status, N_USERS, N_USERS * len(AGENT_TYPES))
    return ok
