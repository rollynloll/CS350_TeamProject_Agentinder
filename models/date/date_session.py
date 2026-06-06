from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple
from uuid import UUID, uuid4

from ..rating.rating import Rating
from ..score.score_manager import ScoreManager, TrustDataPoint
from ..types import Message

if TYPE_CHECKING:
    from ..agent.agent import Agent

logger = logging.getLogger(__name__)

_MAX_TURNS_PER_AGENT = 20
_IMBALANCE_THRESHOLD = 0.80


class DateStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class DateOutcome(str, Enum):
    SUCCESSFUL = "successful"
    NEUTRAL = "neutral"
    UNSUCCESSFUL = "unsuccessful"


@dataclass
class DateResult:
    outcome: DateOutcome
    ratings: List[Rating]
    transcript: List[Message]
    trust_delta: float
    status: DateStatus
    is_imbalanced: bool = False


class IcebreakerGenerator:
    def generate(self, agent_a: Agent, agent_b: Agent) -> str:
        tags_a = set(agent_a.getProfile().capability_tags)
        tags_b = set(agent_b.getProfile().capability_tags)
        common = tags_a & tags_b
        if common:
            tag = next(iter(sorted(common)))
            return f"Let's explore potential collaboration around {tag}."
        all_tags = sorted(tags_a | tags_b)
        if all_tags:
            return f"Tell me about your work in {all_tags[0]} and what collaboration you're looking for."
        return "Tell me about your capabilities and what you're looking for in a collaboration."


class DateSession:
    """두 에이전트가 한 번의 데이트를 완주하는 실행 단위.

    run() 호출 → handshake → date → rating → DateResult 반환.
    각 단계 실패 시 다음 단계로 진행하지 않는다.
    """

    def __init__(
        self,
        agent_a: Agent,
        agent_b: Agent,
        match_id: UUID,
        skip_trust_check: bool,
        topic: Optional[str],
        score_manager: ScoreManager,
        min_trust_threshold: float = 0.3,
        max_turns_per_agent: int = _MAX_TURNS_PER_AGENT,
    ) -> None:
        self._agent_a = agent_a
        self._agent_b = agent_b
        self._match_id = match_id
        self._skip_trust_check = skip_trust_check
        self._topic = topic
        self._score_manager = score_manager
        self._min_trust_threshold = min_trust_threshold
        self._max_turns_per_agent = max_turns_per_agent
        self._date_id: UUID = uuid4()
        self._status: DateStatus = DateStatus.PENDING

    @property
    def date_id(self) -> UUID:
        return self._date_id

    @property
    def match_id(self) -> UUID:
        return self._match_id

    @property
    def status(self) -> DateStatus:
        return self._status

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> DateResult:
        if not self._handshake():
            return DateResult(
                outcome=DateOutcome.UNSUCCESSFUL,
                ratings=[],
                transcript=[],
                trust_delta=0.0,
                status=self._status,
            )

        transcript, is_imbalanced = self._date()

        if self._status == DateStatus.NO_SHOW:
            self._record_noshow()
            return DateResult(
                outcome=DateOutcome.UNSUCCESSFUL,
                ratings=[],
                transcript=transcript,
                trust_delta=0.0,
                status=DateStatus.NO_SHOW,
                is_imbalanced=is_imbalanced,
            )

        outcome, trust_delta, ratings = self._rating(transcript)
        self._status = DateStatus.COMPLETED
        return DateResult(
            outcome=outcome,
            ratings=ratings,
            transcript=transcript,
            trust_delta=trust_delta,
            status=DateStatus.COMPLETED,
            is_imbalanced=is_imbalanced,
        )

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _handshake(self) -> bool:
        """신뢰 임계값 확인. skip_trust_check=True면 무조건 통과."""
        if self._skip_trust_check:
            self._status = DateStatus.IN_PROGRESS
            return True

        trust_a = self._score_manager.getTrust(self._agent_a.agent_id)
        trust_b = self._score_manager.getTrust(self._agent_b.agent_id)

        # None(신규 에이전트)은 임계값 체크 면제
        if trust_a is not None and trust_a < self._min_trust_threshold:
            self._status = DateStatus.CANCELLED
            return False
        if trust_b is not None and trust_b < self._min_trust_threshold:
            self._status = DateStatus.CANCELLED
            return False

        self._status = DateStatus.IN_PROGRESS
        return True

    def _date(self) -> Tuple[List[Message], bool]:
        """두 에이전트가 번갈아 메시지를 주고받는다. (transcript, is_imbalanced) 반환."""
        topic = self._topic
        if topic is None:
            topic = IcebreakerGenerator().generate(self._agent_a, self._agent_b)

        transcript: List[Message] = []
        turn_counts = [0, 0]  # [agent_a_turns, agent_b_turns]
        agents = [self._agent_a, self._agent_b]
        current_content = topic
        current_idx = 0  # agent_a starts

        total_turns = self._max_turns_per_agent * 2

        for turn in range(total_turns):
            current_agent = agents[current_idx]
            llm_client = current_agent.getLLMClient()

            if llm_client is None:
                logger.warning("Agent %s has no LLMClient", current_agent.agent_id)
                self._status = DateStatus.NO_SHOW
                return transcript, self._check_imbalance(turn_counts)

            try:
                # 대화 히스토리 + 현재 입력을 함께 넘김
                history = list(transcript) + [Message(role="user", content=current_content)]
                response = llm_client.generate(history=history, turn_count=turn + 1)
            except Exception as exc:
                logger.error("LLM call failed for agent %s: %s", current_agent.agent_id, exc)
                self._status = DateStatus.NO_SHOW
                return transcript, self._check_imbalance(turn_counts)

            role = "assistant" if current_idx == 0 else "user"
            transcript.append(Message(role=role, content=response))
            turn_counts[current_idx] += 1

            current_content = response
            current_idx = 1 - current_idx

        return transcript, self._check_imbalance(turn_counts)

    def _rating(
        self, transcript: List[Message]
    ) -> Tuple[DateOutcome, float, List[Rating]]:
        """transcript 기반 outcome 결정, 신뢰 점수 반영, Rating 생성."""
        outcome, stars = self._determine_outcome(len(transcript))

        compat = self._score_manager.getCompatibility(
            self._agent_a.getProfile(),
            self._agent_b.getProfile(),
        ).total
        compatibility = round(min(1.0, max(0.0, compat)), 4)

        task_completed = outcome != DateOutcome.UNSUCCESSFUL
        prior_trust_a = self._score_manager.getTrust(self._agent_a.agent_id) or 0.0

        if self._skip_trust_check:
            # 비동기 — 양쪽 모두 자동 평가
            rating_for_b = Rating(
                date_id=self._date_id,
                rater_principal_id=self._agent_a.principal_id,
                rated_agent_id=self._agent_b.agent_id,
                stars=stars,
                compatibility=compatibility,
            )
            rating_for_a = Rating(
                date_id=self._date_id,
                rater_principal_id=self._agent_b.principal_id,
                rated_agent_id=self._agent_a.agent_id,
                stars=stars,
                compatibility=compatibility,
            )
            ratings = [rating_for_b, rating_for_a]

            dp_a = TrustDataPoint(
                agent_id=self._agent_a.agent_id,
                date_id=self._date_id,
                peer_rating=rating_for_a,
                task_completed=task_completed,
            )
            dp_b = TrustDataPoint(
                agent_id=self._agent_b.agent_id,
                date_id=self._date_id,
                peer_rating=rating_for_b,
                task_completed=task_completed,
            )
        else:
            # 동기 — 초대한 쪽(agent_a)이 상대(agent_b)를 평가
            rating_for_b = Rating(
                date_id=self._date_id,
                rater_principal_id=self._agent_a.principal_id,
                rated_agent_id=self._agent_b.agent_id,
                stars=stars,
                compatibility=compatibility,
            )
            ratings = [rating_for_b]

            dp_a = TrustDataPoint(
                agent_id=self._agent_a.agent_id,
                date_id=self._date_id,
                task_completed=task_completed,
            )
            dp_b = TrustDataPoint(
                agent_id=self._agent_b.agent_id,
                date_id=self._date_id,
                peer_rating=rating_for_b,
                task_completed=task_completed,
            )

        self._score_manager.addTrustDataPoint(self._agent_a.agent_id, dp_a)
        self._score_manager.addTrustDataPoint(self._agent_b.agent_id, dp_b)
        self._score_manager.checkUpgrade(self._agent_a.agent_id, self._agent_b.agent_id)

        new_trust_a = self._score_manager.getTrust(self._agent_a.agent_id) or 0.0
        trust_delta = round(new_trust_a - prior_trust_a, 6)

        return outcome, trust_delta, ratings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _determine_outcome(self, transcript_len: int) -> Tuple[DateOutcome, int]:
        max_possible = self._max_turns_per_agent * 2
        if transcript_len >= max_possible * 0.8:
            return DateOutcome.SUCCESSFUL, 5
        if transcript_len >= max_possible * 0.4:
            return DateOutcome.NEUTRAL, 3
        return DateOutcome.UNSUCCESSFUL, 1

    def _check_imbalance(self, turn_counts: List[int]) -> bool:
        total = sum(turn_counts)
        if total == 0:
            return False
        return any(count / total >= _IMBALANCE_THRESHOLD for count in turn_counts)

    def _record_noshow(self) -> None:
        for agent in (self._agent_a, self._agent_b):
            dp = TrustDataPoint(
                agent_id=agent.agent_id,
                date_id=self._date_id,
                task_completed=False,
                is_noshow=True,
            )
            self._score_manager.addTrustDataPoint(agent.agent_id, dp)
