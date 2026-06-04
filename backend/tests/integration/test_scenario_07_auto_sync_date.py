"""
시나리오 7 — 자동 동기 데이트 (STUB).

상태: auto-match 백엔드 로직 미구현 (README V1+). 본 파일은
  (1) 미구현 갭을 명시하는 가드 테스트
  (2) 향후 구현이 만족해야 할 동작 계약을 스텁으로 검증
하는 두 부분으로 구성된다. 구현 완료 시 스텁을 실제 핸들러 호출로 교체.

자동 동기 데이트 = 사람 스와이프 없이 시스템이 최고 호환 후보를 골라
                  매치 → 라이브(동기) 데이트까지 자동 진행.
"""
from __future__ import annotations

from uuid import uuid4

from app.handlers import feed_handler
from models.agent.agent_profile import AgentProfile
from models.enums import VisibilityEnum
from models.score.score_manager import ScoreManager


def make_profile(capability_tags):
    return AgentProfile(
        agent_id=uuid4(),
        display_name="Cand",
        capability_tags=capability_tags,
        style_vector={},
        date_count=10,
        visibility=VisibilityEnum.PUBLIC,
    )


# ── 향후 구현이 만족해야 할 동작 계약 (스텁) ────────────────────────────────

def auto_pick_best_match(sm: ScoreManager, viewer_profile, candidates):
    """STUB: auto-match가 골라야 할 최고 호환 후보 선택 로직.

    실제 구현은 backend AutoMatch 서비스에 들어갈 예정.
    여기서는 ScoreManager.getCompatibility로 랭킹만 검증한다.
    """
    ranked = sorted(
        candidates,
        key=lambda p: sm.getCompatibility(viewer_profile, p).total,
        reverse=True,
    )
    return ranked[0] if ranked else None


class TestAutoMatchContract:
    def test_picks_highest_compatibility_candidate(self) -> None:
        sm = ScoreManager()
        viewer = make_profile(capability_tags=["python", "ml", "nlp"])
        weak = make_profile(capability_tags=["design"])
        strong = make_profile(capability_tags=["python", "ml", "nlp"])

        best = auto_pick_best_match(sm, viewer, [weak, strong])
        assert best is strong  # 태그 겹침 큰 후보 선택

    def test_no_candidates_returns_none(self) -> None:
        sm = ScoreManager()
        viewer = make_profile(capability_tags=["python"])
        assert auto_pick_best_match(sm, viewer, []) is None


class TestAutoMatchGap:
    """auto-match 백엔드 미구현 가드 — 구현되면 실패하며 교체 신호."""

    def test_no_auto_match_route_yet(self) -> None:
        paths = {r.path for r in feed_handler.router.routes}
        auto_paths = {p for p in paths if "auto" in p.lower()}
        assert not auto_paths, \
            f"auto-match 라우트 등장: {auto_paths} → 시나리오 7을 실제 테스트로 교체하세요."

    def test_no_auto_match_service_yet(self) -> None:
        import app.deps as deps
        assert not hasattr(deps, "auto_match_service"), \
            "auto_match_service 등장 → 실제 자동 동기 데이트 테스트로 교체하세요."
