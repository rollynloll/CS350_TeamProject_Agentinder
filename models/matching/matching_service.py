from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from ..date.date_session import DateSession
from ..enums import SwipeEnum


class IMatchingService(ABC):
    """팀원 B가 정의하고 팀원 A가 구현하는 매칭 계약서.

    세 진입점 각각이 어떤 조건으로 DateSession을 생성하는지 규정한다.
    상대가 결정되면 팀원 A의 구현체가 Match 레코드를 DB에 INSERT한 뒤
    DateSession을 생성하여 반환한다.
    """

    @abstractmethod
    def runAsyncMatch(self, agent_id: UUID) -> DateSession:
        """비동기 자율 매칭.

        - 후보 풀: visibility=PUBLIC 에이전트 전체
        - 선택 방식: 랜덤
        - skipTrustCheck: True
        - topic: None (IcebreakerGenerator 자동 생성)
        - 호출자: 백그라운드 스케줄러
        - 항상 DateSession 반환 (null 없음)
        """

    @abstractmethod
    def runAiMatch(self, agent_id: UUID, topic: str) -> Optional[DateSession]:
        """AI 호환성 기반 동기 매칭.

        - 후보 풀: visibility=PUBLIC 에이전트 전체
        - 선택 방식: ScoreManager.getCompatibility() 최고점 1명
        - skipTrustCheck: False
        - topic: 유저가 제공한 대화 또는 프로젝트 주제
        - 호출자: DateHandler (API 요청)
        - 적합한 상대가 없으면 None 반환
        """

    @abstractmethod
    def runSelectMatch(
        self,
        agent_id: UUID,
        target_id: UUID,
        action: SwipeEnum,
        topic: str,
    ) -> Optional[DateSession]:
        """피드에서 직접 선택한 동기 매칭.

        - 후보 풀: 유저가 직접 선택한 상대
        - 선택 방식: mutual swipe 확인 (LIKE / SUPER_LIKE 양방향)
        - skipTrustCheck: False
        - topic: 유저가 제공한 대화 또는 프로젝트 주제
        - action: SwipeEnum.RIGHT(LIKE) / SwipeEnum.UP(SUPER_LIKE) / SwipeEnum.LEFT(PASS)
        - 호출자: FeedHandler (API 요청)
        - mutual swipe일 때만 DateSession 반환, 아니면 None
        """
