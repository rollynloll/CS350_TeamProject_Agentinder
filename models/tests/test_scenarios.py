"""
시나리오 통합 테스트 — BACKEND_INTERFACE.md 기준
단위 테스트와 달리 여러 객체를 함께 엮어 실제 호출 흐름을 검증한다.
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone, timedelta

from models import (
    Agent, AgentProfile, AgentPersonality, AgentService,
    Principal, PrincipalProfile,
    ScoreManager, CompatibilityScore, TrustBreakdown, TrustDataPoint,
    Rating, Match, Message,
)
from models.enums import (
    SwipeEnum, TierEnum, VisibilityEnum, PlanEnum, IssueEnum,
)


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────

def _new_env():
    """테스트마다 격리된 AgentService + ScoreManager 반환."""
    return AgentService(), ScoreManager()


def _new_principal(svc, score_mgr, plan=PlanEnum.FREE, name="Alice"):
    profile = PrincipalProfile(email=f"{name.lower()}@test.com", name=name, plan=plan)
    return Principal(uuid4(), profile, svc, score_mgr)


def _profile_data(name="Bot", tags=None, visibility=VisibilityEnum.PUBLIC,
                  formality=0.5, creativity=0.5, bio=None):
    return {
        "display_name": name,
        "visibility": visibility,
        "capability_tags": tags or ["coding"],
        "personality": {
            "surface": {
                "bio": bio or f"{name}: a helpful AI agent.",
                "style_sliders": {"formality": formality, "creativity": creativity},
            },
            "deep": {
                "thinking_style": "logical",
                "values": ["accuracy", "clarity"],
                "conflict_handling": "reason-first",
            },
            "aspiration": {
                "collaboration_goals": ["review", "mentoring"],
                "interest_domains": ["software"],
            },
        },
    }


def _fill_trust(score_mgr, agent_id, n=5, stars=4,
                is_noshow=False, hallucination=False):
    for _ in range(n):
        r = Rating(
            date_id=uuid4(),
            rater_principal_id=uuid4(),
            rated_agent_id=agent_id,
            stars=stars,
            compatibility=stars / 5.0,
        )
        dp = TrustDataPoint(
            agent_id=agent_id,
            date_id=r.date_id,
            peer_rating=r,
            task_completed=not is_noshow,
            is_noshow=is_noshow,
            hallucination_confirmed=hallucination,
        )
        score_mgr.addTrustDataPoint(agent_id, dp)


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-1 회원가입 / Principal 생성
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario01_PrincipalCreation:
    """새 유저가 서비스에 가입하는 흐름."""

    def test_free_principal_has_max_5_agents(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr, plan=PlanEnum.FREE)
        assert p.profile.max_agents == 5

    def test_premium_principal_has_max_20_agents(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr, plan=PlanEnum.PREMIUM)
        assert p.profile.max_agents == 20

    def test_profile_update_propagates(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        p.updateProfile({"name": "Bob", "email": "bob@test.com", "mfa_enabled": True})
        assert p.profile.name == "Bob"
        assert p.profile.email == "bob@test.com"
        assert p.profile.is_mfa_enabled() is True

    def test_upgrade_plan_increases_max_agents(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr, plan=PlanEnum.FREE)
        assert p.profile.max_agents == 5
        p.updateProfile({"plan": PlanEnum.PREMIUM})
        assert p.profile.max_agents == 20


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-2 에이전트 생성
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario02_AgentCreation:
    """유저가 에이전트를 생성하는 흐름."""

    def test_create_returns_agent_and_one_time_key(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, api_key = p.createAgent(_profile_data("AlphaBot"))
        assert isinstance(agent, Agent)
        assert isinstance(api_key, str) and len(api_key) > 0

    def test_api_key_is_not_stored_as_plaintext(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, api_key = p.createAgent(_profile_data())
        stored = svc._credentials[agent.agent_id]
        assert stored != api_key

    def test_profile_fields_persisted(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data(
            name="AlphaBot",
            tags=["coding", "review"],
            visibility=VisibilityEnum.RESTRICTED,
        ))
        prof = agent.getProfile()
        assert prof.display_name == "AlphaBot"
        assert "review" in prof.capability_tags
        assert prof.visibility == VisibilityEnum.RESTRICTED

    def test_personality_system_prompt_pre_cached(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data(bio="I am a coder."))
        assert agent.getPersonality().system_prompt_cache is not None
        assert "coder" in agent.getPersonality().system_prompt_cache

    def test_style_vector_synced_from_personality(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data(formality=0.9, creativity=0.2))
        assert agent.getProfile().style_vector["formality"] == 0.9

    def test_agent_appears_in_principal_agents(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        assert agent in p.agents

    def test_free_plan_hard_limit_5(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr, plan=PlanEnum.FREE)
        for i in range(5):
            p.createAgent(_profile_data(f"Bot{i}"))
        with pytest.raises(PermissionError):
            p.createAgent(_profile_data("Bot6"))

    def test_duplicate_name_same_principal_raises(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        p.createAgent(_profile_data("SameName"))
        with pytest.raises(ValueError, match="SameName"):
            p.createAgent(_profile_data("SameName"))

    def test_duplicate_name_different_principal_allowed(self):
        svc, smgr = _new_env()
        p1 = _new_principal(svc, smgr, name="Alice")
        p2 = _new_principal(svc, smgr, name="Bob")
        p1.createAgent(_profile_data("SharedBot"))
        p2.createAgent(_profile_data("SharedBot"))  # 에러 없어야 함

    def test_new_agent_starts_as_new_agent(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        assert agent.isNewAgent() is True
        assert agent.getProfile().tier_badge == "new_agent"


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-3 에이전트 수정
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario03_AgentUpdate:
    """유저가 에이전트를 수정하는 흐름."""

    def test_update_display_name(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data("OldName"))
        p.updateAgent(agent.agent_id, {"display_name": "NewName"})
        assert agent.getProfile().display_name == "NewName"

    def test_update_personality_regenerates_prompt_cache(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data(bio="Original bio."))
        old_cache = agent.getPersonality().system_prompt_cache
        p.updateAgent(agent.agent_id, {
            "personality": {"surface": {"bio": "Completely new bio."}},
        })
        new_cache = agent.getPersonality().system_prompt_cache
        assert new_cache != old_cache
        assert "Completely new bio" in new_cache

    def test_update_personality_syncs_style_vector(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data(formality=0.5))
        p.updateAgent(agent.agent_id, {
            "personality": {
                "surface": {"bio": "Updated.", "style_sliders": {"formality": 0.95}},
            },
        })
        assert agent.getProfile().style_vector["formality"] == 0.95

    def test_update_capability_tags(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data(tags=["coding"]))
        p.updateAgent(agent.agent_id, {"capability_tags": ["coding", "design", "ux"]})
        assert "design" in agent.getProfile().capability_tags

    def test_update_llm_model_rebuilds_client(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        old_client = agent.getLLMClient()
        p.updateAgent(agent.agent_id, {"llm_model": "gpt-4-turbo"})
        new_client = agent.getLLMClient()
        assert new_client is not old_client
        assert new_client.model == "gpt-4-turbo"

    def test_update_wrong_owner_raises_permission_error(self):
        svc, smgr = _new_env()
        p1 = _new_principal(svc, smgr, name="Alice")
        p2 = _new_principal(svc, smgr, name="Bob")
        agent, _ = p1.createAgent(_profile_data())
        with pytest.raises(PermissionError):
            p2.updateAgent(agent.agent_id, {"display_name": "Hijacked"})


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-4 피드 조회 — 호환성 점수 기반 정렬
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario04_FeedCompatibility:
    """피드에서 에이전트 목록을 호환성 점수로 정렬하는 흐름."""

    def _make_feed_data(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)

        # viewer: coding + analysis
        viewer, _ = p.createAgent(_profile_data(
            "Viewer", tags=["coding", "analysis"],
            formality=0.7, creativity=0.3,
        ))
        # highly compatible: coding + analysis (tags 100% 겹침, style 유사)
        high, _ = p.createAgent(_profile_data(
            "HighMatch", tags=["coding", "analysis"],
            formality=0.7, creativity=0.3,
        ))
        # low compatible: completely different tags, opposite style
        low, _ = p.createAgent(_profile_data(
            "LowMatch", tags=["design", "ux"],
            formality=0.1, creativity=0.9,
        ))
        return smgr, viewer, high, low

    def test_identical_tags_give_higher_score(self):
        smgr, viewer, high, low = self._make_feed_data()
        score_high = smgr.getCompatibility(viewer.getProfile(), high.getProfile())
        score_low = smgr.getCompatibility(viewer.getProfile(), low.getProfile())
        assert score_high.total > score_low.total

    def test_score_is_directional(self):
        """S(A→B) ≠ S(B→A) when trust scores differ."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A", tags=["coding"]))
        b, _ = p.createAgent(_profile_data("B", tags=["coding"]))

        # B에게만 신뢰 점수 부여
        _fill_trust(smgr, b.agent_id, n=5, stars=5)
        # B의 date_count를 5 이상으로 설정 (신규 에이전트 아님)
        b.getProfile().date_count = 5

        score_ab = smgr.getCompatibility(a.getProfile(), b.getProfile())
        score_ba = smgr.getCompatibility(b.getProfile(), a.getProfile())
        assert score_ab.trust_score > score_ba.trust_score

    def test_new_agent_excludes_trust_component(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        viewer, _ = p.createAgent(_profile_data("Viewer", tags=["coding"]))
        new_bot, _ = p.createAgent(_profile_data("NewBot", tags=["coding"]))
        # new_bot은 date_count=0 → isNewAgent=True
        _fill_trust(smgr, new_bot.agent_id, n=5, stars=5)

        score = smgr.getCompatibility(viewer.getProfile(), new_bot.getProfile())
        assert score.trust_score == 0.0

    def test_explain_shows_common_tags(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A", tags=["coding", "testing"]))
        b, _ = p.createAgent(_profile_data("B", tags=["coding", "design"]))
        bd = smgr.explain(a.getProfile(), b.getProfile())
        assert "coding" in bd.common_tags
        assert "testing" in bd.complementary_tags
        assert "design" in bd.complementary_tags

    def test_hidden_agent_filtered_from_feed(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        viewer, _ = p.createAgent(_profile_data("Viewer"))
        hidden, _ = p.createAgent(_profile_data(
            "Hidden", visibility=VisibilityEnum.HIDDEN,
        ))
        # HIDDEN 에이전트는 isVisibleTo로 걸러짐
        assert hidden.isVisibleTo(1.0) is False

    def test_restricted_agent_visible_above_threshold(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        restricted, _ = p.createAgent(_profile_data(
            "Restricted", visibility=VisibilityEnum.RESTRICTED,
        ))
        assert restricted.isVisibleTo(0.5) is True
        assert restricted.isVisibleTo(0.49) is False


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-5 스와이프 / 매칭
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario05_Swipe:
    """에이전트가 다른 에이전트를 스와이프하는 흐름."""

    def test_right_swipe_returns_match(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        match = a.swipe(b.agent_id, SwipeEnum.RIGHT)
        assert isinstance(match, Match)
        assert match.agent_a_id == a.agent_id
        assert match.agent_b_id == b.agent_id

    def test_left_swipe_returns_none(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        result = a.swipe(b.agent_id, SwipeEnum.LEFT)
        assert result is None

    def test_super_like_returns_match(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        match = a.swipe(b.agent_id, SwipeEnum.UP)
        assert isinstance(match, Match)

    def test_match_ids_are_stable(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        match = a.swipe(b.agent_id, SwipeEnum.RIGHT)
        assert match.match_id is not None
        assert isinstance(match.match_id, UUID)


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-6 매치 승인·거절
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario06_MatchApproval:
    """주인이 매치를 승인하거나 거절하는 흐름."""

    def test_approve_does_not_raise(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        p.approveMatch(uuid4())

    def test_reject_does_not_raise(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        p.rejectMatch(uuid4())

    def test_approve_then_reject_different_matches(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        p.approveMatch(uuid4())
        p.rejectMatch(uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-7 커피챗 — 메시지 전송
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario07_SendMessage:
    """에이전트가 성격 일관성을 유지하며 메시지를 응답하는 흐름."""

    def test_send_message_returns_string(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        response = agent.sendMessage(uuid4(), "안녕하세요!")
        assert isinstance(response, str)

    def test_send_message_without_llm_client_raises(self):
        from models.agent.agent_personality import AgentPersonality
        from models.agent.agent_profile import AgentProfile
        agent_id = uuid4()
        agent = Agent(
            agent_id=agent_id,
            principal_id=uuid4(),
            profile=AgentProfile(agent_id=agent_id, display_name="NakedBot"),
            personality=AgentPersonality(),
            llm_client=None,
        )
        with pytest.raises(RuntimeError):
            agent.sendMessage(uuid4(), "Hello")

    def test_send_message_delegates_to_llm_client(self):
        from unittest.mock import MagicMock
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        mock_client = MagicMock()
        mock_client.generate.return_value = "테스트 응답"
        agent.setLLMClient(mock_client)
        response = agent.sendMessage(uuid4(), "질문입니다.")
        assert response == "테스트 응답"
        mock_client.generate.assert_called_once()

    def test_personality_available_during_generate(self):
        """LLMClient가 generate 시 최신 personality를 참조하는지 확인."""
        from unittest.mock import MagicMock
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data(bio="Original bio."))

        captured = {}
        mock_client = MagicMock()
        def capture_generate(history, turn_count):
            # agent.getPersonality()를 호출해 성격이 최신인지 확인
            captured["personality"] = agent.getPersonality()
            return "응답"
        mock_client.generate.side_effect = capture_generate
        agent.setLLMClient(mock_client)

        # personality 수정 후 sendMessage
        agent.setPersonality({"surface": {"bio": "Updated bio."}})
        agent.sendMessage(uuid4(), "Hello")
        assert "Updated bio" in captured["personality"].system_prompt_cache


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-8 데이트 시작·종료
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario08_DateLifecycle:
    """데이트 시작부터 종료까지의 상태 변화 흐름."""

    def test_join_makes_agent_active(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        assert agent.isActive() is False
        date_id = uuid4()
        agent.joinDate(date_id)
        assert agent.isActive() is True

    def test_leave_makes_agent_inactive(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        date_id = uuid4()
        agent.joinDate(date_id)
        agent.leaveDate(date_id)
        assert agent.isActive() is False

    def test_leave_increments_date_count(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        date_id = uuid4()
        agent.joinDate(date_id)
        assert agent.getProfile().date_count == 0
        agent.leaveDate(date_id)
        assert agent.getProfile().date_count == 1

    def test_five_dates_transitions_out_of_new_agent(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        for _ in range(5):
            did = uuid4()
            agent.joinDate(did)
            agent.leaveDate(did)
        assert agent.isNewAgent() is False
        assert agent.getProfile().tier_badge == "5"

    def test_both_agents_join_and_leave(self):
        """두 에이전트가 함께 데이트를 진행하는 흐름."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        date_id = uuid4()
        a.joinDate(date_id)
        b.joinDate(date_id)
        assert a.isActive() and b.isActive()
        a.leaveDate(date_id)
        b.leaveDate(date_id)
        assert not a.isActive() and not b.isActive()
        assert a.getProfile().date_count == 1
        assert b.getProfile().date_count == 1

    def test_multiple_concurrent_dates_tracked(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        d1, d2 = uuid4(), uuid4()
        agent.joinDate(d1)
        agent.joinDate(d2)
        agent.leaveDate(d1)
        assert agent.isActive() is True  # d2 still active
        agent.leaveDate(d2)
        assert agent.isActive() is False


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-9 데이트 후 평가 제출
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario09_RatingSubmission:
    """데이트가 끝난 후 주인이 평가를 제출하는 흐름."""

    def test_submit_rating_updates_trust(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        _, _ = p.createAgent(_profile_data("Rater"))
        rated, _ = p.createAgent(_profile_data("Rated"))

        for _ in range(5):
            r = Rating(
                date_id=uuid4(),
                rater_principal_id=p.principal_id,
                rated_agent_id=rated.agent_id,
                stars=5, compatibility=1.0,
            )
            p.submitRating(r.date_id, r)

        trust = smgr.getTrust(rated.agent_id)
        assert trust is not None and trust > 0.0

    def test_trust_cached_on_agent_after_submit(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        rated, _ = p.createAgent(_profile_data("Rated"))
        for _ in range(5):
            r = Rating(
                date_id=uuid4(),
                rater_principal_id=p.principal_id,
                rated_agent_id=rated.agent_id,
                stars=4, compatibility=0.8,
            )
            p.submitRating(r.date_id, r)
        assert rated.getTrustScore() is not None

    def test_rating_with_hallucination_lowers_trust(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        clean, _ = p.createAgent(_profile_data("Clean"))
        halluc, _ = p.createAgent(_profile_data("Halluc"))

        for agent in [clean, halluc]:
            for _ in range(5):
                r = Rating(
                    date_id=uuid4(),
                    rater_principal_id=p.principal_id,
                    rated_agent_id=agent.agent_id,
                    stars=4, compatibility=0.8,
                )
                p.submitRating(r.date_id, r)

        r_h = Rating(
            date_id=uuid4(),
            rater_principal_id=p.principal_id,
            rated_agent_id=halluc.agent_id,
            stars=4, compatibility=0.8,
            issues=[IssueEnum.HALLUCINATION],
        )
        p.submitRating(r_h.date_id, r_h)

        assert smgr.getTrust(halluc.agent_id) < smgr.getTrust(clean.agent_id)

    def test_noshow_penalty_applies(self):
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        reliable, _ = p.createAgent(_profile_data("Reliable"))
        noshow, _ = p.createAgent(_profile_data("Noshow"))

        for agent in [reliable, noshow]:
            for _ in range(5):
                r = Rating(
                    date_id=uuid4(),
                    rater_principal_id=p.principal_id,
                    rated_agent_id=agent.agent_id,
                    stars=4, compatibility=0.8,
                )
                p.submitRating(r.date_id, r)

        dp_noshow = TrustDataPoint(
            agent_id=noshow.agent_id,
            date_id=uuid4(),
            task_completed=False,
            is_noshow=True,
        )
        smgr.addTrustDataPoint(noshow.agent_id, dp_noshow)
        assert smgr.getTrust(noshow.agent_id) < smgr.getTrust(reliable.agent_id)

    def test_rating_locked_after_72h(self):
        r = Rating(
            date_id=uuid4(), rater_principal_id=uuid4(),
            rated_agent_id=uuid4(), stars=3, compatibility=0.6,
        )
        r.created_at = datetime.now(timezone.utc) - timedelta(hours=73)
        with pytest.raises(PermissionError):
            r.update({"stars": 5})
        assert r.is_locked is True

    def test_rating_editable_within_72h(self):
        r = Rating(
            date_id=uuid4(), rater_principal_id=uuid4(),
            rated_agent_id=uuid4(), stars=3, compatibility=0.6,
        )
        r.update({"stars": 5, "comments": "Changed my mind."})
        assert r.stars == 5

    def test_to_trust_data_point_preserves_hallucination_flag(self):
        r = Rating(
            date_id=uuid4(), rater_principal_id=uuid4(),
            rated_agent_id=uuid4(), stars=2, compatibility=0.3,
            issues=[IssueEnum.HALLUCINATION],
        )
        dp = r.to_trust_data_point()
        assert dp.hallucination_confirmed is True
        assert dp.peer_rating is r


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-10 신뢰 점수 조회
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario10_TrustScore:
    """신뢰 점수 조회 및 분해 흐름."""

    def test_none_before_5_data_points(self):
        _, smgr = _new_env()
        aid = uuid4()
        _fill_trust(smgr, aid, n=4)
        assert smgr.getTrust(aid) is None

    def test_not_none_after_5_data_points(self):
        _, smgr = _new_env()
        aid = uuid4()
        _fill_trust(smgr, aid, n=5)
        assert smgr.getTrust(aid) is not None

    def test_breakdown_formula_v1(self):
        """composite = 0.5 × peer_avg + 0.3 × task_rate (V1, other=0)."""
        _, smgr = _new_env()
        aid = uuid4()
        _fill_trust(smgr, aid, n=5, stars=5)  # 5★, all completed
        bd = smgr.getTrustBreakdown(aid)
        expected = 0.50 * 1.0 + 0.30 * 1.0
        assert abs(bd.composite - expected) < 1e-6

    def test_perfect_vs_minimum_trust(self):
        _, smgr = _new_env()
        perfect = uuid4()
        minimal = uuid4()
        _fill_trust(smgr, perfect, n=5, stars=5)
        _fill_trust(smgr, minimal, n=5, stars=1)
        assert smgr.getTrust(perfect) > smgr.getTrust(minimal)

    def test_trust_score_not_transferred_between_agents(self):
        """같은 주인이라도 에이전트 간 점수 이전 불가."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))
        _fill_trust(smgr, a.agent_id, n=5, stars=5)
        # A에게 신뢰 점수가 있어도 B는 없어야 함
        assert smgr.getTrust(b.agent_id) is None

    def test_breakdown_data_point_count_accurate(self):
        _, smgr = _new_env()
        aid = uuid4()
        _fill_trust(smgr, aid, n=7)
        bd = smgr.getTrustBreakdown(aid)
        assert bd.data_point_count == 7


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-11 관계 단계 조회 및 승급
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario11_RelationshipTier:
    """두 에이전트 간 관계 단계가 시간에 따라 승급하는 흐름."""

    def _progress_to(self, smgr, a_id, b_id, target_tier: TierEnum):
        """target_tier까지 관계를 진행시키는 헬퍼."""
        rel = smgr._get_or_create_rel(a_id, b_id)
        tier_dates = {
            TierEnum.ACQUAINTANCE: 1,
            TierEnum.COLLEAGUE: 3,
            TierEnum.TRUSTED_PARTNER: 10,
        }
        for tier, n in tier_dates.items():
            if rel.successful_dates < n:
                rel.successful_dates = n
            if tier == TierEnum.TRUSTED_PARTNER:
                rel.avg_rating = 4.0
            smgr.checkUpgrade(a_id, b_id)
            if tier == target_tier:
                break

    def test_initial_tier_is_stranger(self):
        _, smgr = _new_env()
        assert smgr.getRelationship(uuid4(), uuid4()) == TierEnum.STRANGER

    def test_full_tier_progression(self):
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()

        # STRANGER → ACQUAINTANCE
        rel = smgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        assert smgr.checkUpgrade(a, b) == TierEnum.ACQUAINTANCE

        # ACQUAINTANCE → COLLEAGUE
        rel.successful_dates = 3
        assert smgr.checkUpgrade(a, b) == TierEnum.COLLEAGUE

        # COLLEAGUE → TRUSTED_PARTNER
        rel.successful_dates = 10
        rel.avg_rating = 4.0
        assert smgr.checkUpgrade(a, b) == TierEnum.TRUSTED_PARTNER
        assert smgr.getRelationship(a, b) == TierEnum.TRUSTED_PARTNER

    def test_no_upgrade_below_threshold(self):
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        rel = smgr._get_or_create_rel(a, b)
        rel.successful_dates = 0
        assert smgr.checkUpgrade(a, b) is None

    def test_trusted_partner_requires_avg_rating_4(self):
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        rel = smgr._get_or_create_rel(a, b)
        rel.successful_dates = 3
        smgr.checkUpgrade(a, b)  # STRANGER → ACQUAINTANCE
        smgr.checkUpgrade(a, b)  # ACQUAINTANCE → COLLEAGUE
        rel.successful_dates = 10
        rel.avg_rating = 3.9  # 미달
        result = smgr.checkUpgrade(a, b)
        assert result is None

    def test_relationship_is_symmetric_by_key(self):
        """(a, b) 와 (b, a) 는 같은 관계를 조회한다."""
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        rel = smgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        smgr.checkUpgrade(a, b)
        assert smgr.getRelationship(b, a) == TierEnum.ACQUAINTANCE

    def test_record_successful_date_running_average(self):
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        smgr.recordSuccessfulDate(a, b, rating=4.0)
        smgr.recordSuccessfulDate(a, b, rating=2.0)
        rel = smgr._get_or_create_rel(a, b)
        assert abs(rel.avg_rating - 3.0) < 1e-6
        assert rel.successful_dates == 2

    def test_checkupgrade_one_step_at_a_time(self):
        """단 한 번의 checkUpgrade로 STRANGER→COLLEAGUE가 되지 않음."""
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        rel = smgr._get_or_create_rel(a, b)
        rel.successful_dates = 10
        rel.avg_rating = 5.0
        # 첫 호출: STRANGER → ACQUAINTANCE (날짜 >= 1 조건 충족)
        first = smgr.checkUpgrade(a, b)
        assert first == TierEnum.ACQUAINTANCE
        # 두 번째 호출: ACQUAINTANCE → COLLEAGUE
        second = smgr.checkUpgrade(a, b)
        assert second == TierEnum.COLLEAGUE


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3-12 관계 동결·해제
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario12_FreezeUnfreeze:
    """신뢰 점수 하락 시 관계 단계를 동결하고 회복 후 해제하는 흐름."""

    def test_freeze_blocks_upgrade(self):
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        smgr.freeze(a, b)
        rel = smgr._get_or_create_rel(a, b)
        rel.successful_dates = 5
        assert smgr.checkUpgrade(a, b) is None

    def test_freeze_preserves_current_tier(self):
        """동결 중에는 현재 단계가 유지된다 (다운그레이드 없음)."""
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        rel = smgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        smgr.checkUpgrade(a, b)  # → ACQUAINTANCE
        smgr.freeze(a, b)
        # 동결 이후 승급 시도해도 현재 단계 유지
        rel.successful_dates = 10
        smgr.checkUpgrade(a, b)
        assert smgr.getRelationship(a, b) == TierEnum.ACQUAINTANCE

    def test_unfreeze_allows_upgrade(self):
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        smgr.freeze(a, b)
        smgr.unfreeze(a, b)
        rel = smgr._get_or_create_rel(a, b)
        rel.successful_dates = 1
        result = smgr.checkUpgrade(a, b)
        assert result == TierEnum.ACQUAINTANCE

    def test_freeze_is_symmetric(self):
        """(a, b) 동결은 (b, a) 방향에도 동일하게 적용된다."""
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        smgr.freeze(a, b)
        rel = smgr._get_or_create_rel(b, a)
        assert rel.is_frozen is True

    def test_freeze_unfreeze_cycle(self):
        _, smgr = _new_env()
        a, b = uuid4(), uuid4()
        smgr.freeze(a, b)
        assert smgr._get_or_create_rel(a, b).is_frozen is True
        smgr.unfreeze(a, b)
        assert smgr._get_or_create_rel(a, b).is_frozen is False


# ─────────────────────────────────────────────────────────────────────────────
# 통합 엔드투엔드 시나리오 — 전체 데이팅 플로우
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEnd_FullDatingFlow:
    """
    신규 유저 가입 → 에이전트 생성 → 피드 탐색 → 스와이프 → 매칭
    → 커피챗 → 데이트 → 평가 → 신뢰 점수 → 관계 승급 까지의 전체 흐름.
    """

    def test_full_flow_from_signup_to_tier_upgrade(self):
        svc, smgr = _new_env()

        # 1. 두 유저 가입
        alice = _new_principal(svc, smgr, name="Alice", plan=PlanEnum.PREMIUM)
        bob = _new_principal(svc, smgr, name="Bob", plan=PlanEnum.PREMIUM)

        # 2. 각자 에이전트 생성
        alpha, alpha_key = alice.createAgent(_profile_data(
            "Alpha", tags=["coding", "analysis"], formality=0.8,
        ))
        beta, beta_key = bob.createAgent(_profile_data(
            "Beta", tags=["coding", "testing"], formality=0.7,
        ))
        assert alpha.isNewAgent() and beta.isNewAgent()
        assert alpha_key != beta_key

        # 3. 피드: Alpha → Beta 호환성 확인
        score = smgr.getCompatibility(alpha.getProfile(), beta.getProfile())
        assert score.total > 0.0
        assert "coding" in score.common_tags

        # 4. 스와이프
        match = alpha.swipe(beta.agent_id, SwipeEnum.RIGHT)
        assert isinstance(match, Match)

        # 5. 매치 승인
        alice.approveMatch(match.match_id)

        # 6. 커피챗 — mock LLM
        from unittest.mock import MagicMock
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "안녕하세요! 협업 제안 감사합니다."
        alpha.setLLMClient(mock_llm)
        response = alpha.sendMessage(match.match_id, "함께 작업해볼까요?")
        assert isinstance(response, str)

        # 7. 데이트 시작 및 종료
        date_id = uuid4()
        alpha.joinDate(date_id)
        beta.joinDate(date_id)
        assert alpha.isActive() and beta.isActive()
        alpha.leaveDate(date_id)
        beta.leaveDate(date_id)
        assert not alpha.isActive() and not beta.isActive()
        assert alpha.getProfile().date_count == 1

        # 8. 평가 제출 (5회 반복해 신뢰 점수 산출)
        for _ in range(4):  # 이미 1회 완료, 총 5회
            r_a = Rating(
                date_id=uuid4(), rater_principal_id=alice.principal_id,
                rated_agent_id=beta.agent_id, stars=4, compatibility=0.85,
            )
            alice.submitRating(r_a.date_id, r_a)

        # 첫 번째 date의 평가도 포함
        r_first = Rating(
            date_id=date_id, rater_principal_id=alice.principal_id,
            rated_agent_id=beta.agent_id, stars=5, compatibility=0.9,
        )
        alice.submitRating(r_first.date_id, r_first)

        # 9. 신뢰 점수 확인
        trust = smgr.getTrust(beta.agent_id)
        assert trust is not None and trust > 0.0
        breakdown = smgr.getTrustBreakdown(beta.agent_id)
        assert breakdown.data_point_count == 5

        # 10. 관계 승급 확인 (1회 데이트 → ACQUAINTANCE)
        smgr.recordSuccessfulDate(alpha.agent_id, beta.agent_id, rating=4.5)
        new_tier = smgr.checkUpgrade(alpha.agent_id, beta.agent_id)
        assert new_tier == TierEnum.ACQUAINTANCE
        assert smgr.getRelationship(alpha.agent_id, beta.agent_id) == TierEnum.ACQUAINTANCE

    def test_trust_score_none_before_sufficient_data(self):
        """평가 5개 미만이면 신뢰 점수가 없다."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        agent, _ = p.createAgent(_profile_data())
        for _ in range(4):
            r = Rating(
                date_id=uuid4(), rater_principal_id=p.principal_id,
                rated_agent_id=agent.agent_id, stars=5, compatibility=1.0,
            )
            p.submitRating(r.date_id, r)
        assert smgr.getTrust(agent.agent_id) is None
        # 5번째 제출 후 확인
        r5 = Rating(
            date_id=uuid4(), rater_principal_id=p.principal_id,
            rated_agent_id=agent.agent_id, stars=5, compatibility=1.0,
        )
        p.submitRating(r5.date_id, r5)
        assert smgr.getTrust(agent.agent_id) is not None

    def test_repeated_bad_dates_lowers_trust_and_freezes(self):
        """노쇼+환각이 쌓이면 신뢰가 낮아지고 관계 동결로 이어지는 흐름."""
        svc, smgr = _new_env()
        p = _new_principal(svc, smgr)
        a, _ = p.createAgent(_profile_data("A"))
        b, _ = p.createAgent(_profile_data("B"))

        # 첫 1회 데이트로 ACQUAINTANCE 달성
        smgr.recordSuccessfulDate(a.agent_id, b.agent_id, rating=4.0)
        smgr.checkUpgrade(a.agent_id, b.agent_id)
        assert smgr.getRelationship(a.agent_id, b.agent_id) == TierEnum.ACQUAINTANCE

        # B에게 노쇼 데이터 누적
        for _ in range(5):
            dp = TrustDataPoint(
                agent_id=b.agent_id, date_id=uuid4(),
                task_completed=False, is_noshow=True,
            )
            smgr.addTrustDataPoint(b.agent_id, dp)

        # 신뢰 점수가 낮으면 관계 동결
        smgr.freeze(a.agent_id, b.agent_id)
        rel = smgr._get_or_create_rel(a.agent_id, b.agent_id)
        rel.successful_dates = 10
        result = smgr.checkUpgrade(a.agent_id, b.agent_id)
        assert result is None  # 동결 중 승급 불가
        assert smgr.getRelationship(a.agent_id, b.agent_id) == TierEnum.ACQUAINTANCE
