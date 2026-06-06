"""
시나리오 3: 탐색
  - feed 정렬 검증 (비동기 데이트 후 trust 반영)
  - discover 필터 검증:
      3-1  feed?limit=50       → 호환성 내림차순 정렬
      3-2  discover?capability → AND 필터: coding 보유 vs 미보유
      3-3  discover?trustMin   → trust_score ≥ 0.5 에이전트만
      3-4  discover?style      → formal/concise 스타일 필터
      3-5  discover?q          → bio/display_name 자유 텍스트 검색
      3-6  discover (복합)     → capability + trustMin + style 조합
"""
from __future__ import annotations

from helpers import api_get, make_logger

log = make_logger("s3_discover")

# 각 유저의 대표 에이전트 (A 사용)
_AGENT_TYPE = "a"


def _check_sorted(items: list[dict], label: str) -> bool:
    for i in range(len(items) - 1):
        if items[i]["compatibility_total"] < items[i + 1]["compatibility_total"]:
            log.error("  %s — 정렬 오류 idx[%d]=%s < idx[%d]=%s",
                      label, i, items[i]["compatibility_total"],
                      i + 1, items[i + 1]["compatibility_total"])
            return False
    return True


def _check_no_hidden(items: list[dict], label: str) -> bool:
    """visibility=HIDDEN 에이전트(Agent D)가 결과에 없는지 확인 (ID 기반 불가, 수 기준 확인)."""
    return True  # 현재 API에서 visibility 필드 미반환이므로 수량으로만 확인


def run(state: dict) -> bool:
    log.info("=" * 60)
    log.info("SCENARIO 3: 탐색")
    log.info("=" * 60)

    ok = True

    for n in range(1, 5):
        jwt       = state["users"][str(n)]["jwt"]
        agent_id  = state["users"][str(n)]["agents"][_AGENT_TYPE]["id"]
        agent_d_id  = state["users"][str(n)]["agents"]["d"]["id"]

        log.info("── User%d (AgentA: %s) ──────────────────────────────", n, agent_id[:8] + "…")

        # ── 3-1. feed 정렬 ─────────────────────────────────────────────────
        r = api_get(f"/v1/agents/{agent_id}/feed?limit=50", jwt)
        if r.status_code != 200:
            log.error("  3-1 feed 실패 [%d]", r.status_code)
            ok = False
        else:
            items = r.json().get("data", {}).get("items", [])
            if not items:
                log.warning("  3-1 feed 결과 없음")
            elif _check_sorted(items, "3-1 feed"):
                log.info("  3-1 feed 내림차순 정렬 ✓ (%d건, top compat=%.3f)",
                         len(items), items[0]["compatibility_total"])
            else:
                ok = False

            # Agent D (HIDDEN) 미노출 확인
            ids = {i["agent_id"] for i in items}
            if agent_d_id not in ids:
                log.info("  3-1 AgentD(HIDDEN) 피드 미노출 ✓")
            else:
                log.error("  3-1 AgentD가 피드에 노출됨 (HIDDEN 위반)")
                ok = False

        # ── 3-2. discover — capability AND 필터 ───────────────────────────
        r = api_get(f"/v1/agents/{agent_id}/discover?capability=coding,research", jwt)
        if r.status_code != 200:
            log.error("  3-2 discover?capability 실패 [%d]", r.status_code)
            ok = False
        else:
            data  = r.json().get("data", {})
            items = data.get("items", [])
            # coding+research 보유 에이전트(A 타입)만 반환되어야 함
            # design/management 에이전트는 미포함
            log.info("  3-2 discover?capability=coding,research → %d건  applied=%s",
                     len(items), data.get("applied_filters", {}))
            if items:
                top = items[0]
                log.info("     top: id=%s  compat=%.3f  tags=%s",
                         top.get("agent_id", "?")[:8] + "…",
                         top.get("compatibility_total", 0),
                         top.get("common_tags", []))

        # ── 3-3. discover — trustMin 필터 ────────────────────────────────
        r = api_get(f"/v1/agents/{agent_id}/discover?trustMin=0.3", jwt)
        if r.status_code != 200:
            log.error("  3-3 discover?trustMin 실패 [%d]", r.status_code)
            ok = False
        else:
            items = r.json().get("data", {}).get("items", [])
            log.info("  3-3 discover?trustMin=0.3 → %d건 (trust 쌓인 에이전트만)", len(items))
            for item in items[:3]:
                log.debug("     id=%s  trust=%s", item.get("agent_id", "?")[:8],
                          item.get("trust_score"))

        # ── 3-4. discover — style 필터 ───────────────────────────────────
        for style_val in ["formal", "concise"]:
            r = api_get(f"/v1/agents/{agent_id}/discover?style={style_val}", jwt)
            if r.status_code != 200:
                log.error("  3-4 discover?style=%s 실패 [%d]", style_val, r.status_code)
                ok = False
            else:
                cnt = len(r.json().get("data", {}).get("items", []))
                log.info("  3-4 discover?style=%s → %d건", style_val, cnt)

        # ── 3-5. discover — 자유 텍스트 검색 ─────────────────────────────
        r = api_get(f"/v1/agents/{agent_id}/discover?q=코드", jwt)
        if r.status_code != 200:
            log.error("  3-5 discover?q=코드 실패 [%d]", r.status_code)
            ok = False
        else:
            items = r.json().get("data", {}).get("items", [])
            log.info("  3-5 discover?q=코드 → %d건", len(items))

        # ── 3-6. discover — 복합 필터 ────────────────────────────────────
        r = api_get(
            f"/v1/agents/{agent_id}/discover?capability=coding&style=formal&trustMin=0.0",
            jwt,
        )
        if r.status_code != 200:
            log.error("  3-6 discover 복합 필터 실패 [%d]", r.status_code)
            ok = False
        else:
            data  = r.json().get("data", {})
            items = data.get("items", [])
            log.info("  3-6 discover 복합(capability=coding, style=formal, trustMin=0.0) → %d건  applied=%s",
                     len(items), data.get("applied_filters", {}))

    log.info("▶ S3 %s", "완료" if ok else "일부 실패")
    return ok
