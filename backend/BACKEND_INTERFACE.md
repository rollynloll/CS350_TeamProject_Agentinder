# Agentinder — Backend B 인터페이스 문서

**대상:** 팀원 A (백엔드 / REST API 담당)  
**목적:** `models/` 패키지가 제공하는 객체, 메서드, 호출 시나리오를 설명한다.  
**원칙:** 팀원 A는 `models/` 내부 구현을 직접 수정하지 않는다. 이 문서에 있는 공개 인터페이스만 호출한다.

---

## 목차

1. [초기 설정 — 의존성 주입](#1-초기-설정--의존성-주입)
2. [핵심 객체 레퍼런스](#2-핵심-객체-레퍼런스)
3. [시나리오별 호출 흐름](#3-시나리오별-호출-흐름)
   - [3-1. 회원가입 / Principal 생성](#3-1-회원가입--principal-생성)
   - [3-2. 에이전트 생성](#3-2-에이전트-생성)
   - [3-3. 에이전트 수정](#3-3-에이전트-수정)
   - [3-4. 피드 조회 — 호환성 점수 기반 정렬](#3-4-피드-조회--호환성-점수-기반-정렬)
   - [3-5. 스와이프 / 매칭](#3-5-스와이프--매칭)
   - [3-6. 매치 승인·거절 (Principal)](#3-6-매치-승인거절-principal)
   - [3-7. 커피챗 — 메시지 전송](#3-7-커피챗--메시지-전송)
   - [3-8. 데이트 시작·종료](#3-8-데이트-시작종료)
   - [3-9. 데이트 후 평가 제출](#3-9-데이트-후-평가-제출)
   - [3-10. 신뢰 점수 조회](#3-10-신뢰-점수-조회)
   - [3-11. 관계 단계 조회 및 승급 확인](#3-11-관계-단계-조회-및-승급-확인)
   - [3-12. 관계 동결·해제](#3-12-관계-동결해제)
4. [공개 인터페이스 빠른 참조표](#4-공개-인터페이스-빠른-참조표)
5. [에러 처리](#5-에러-처리)
6. [설계 제약 — 팀원 A가 알아야 할 것](#6-설계-제약--팀원-a가-알아야-할-것)

---

## 1. 초기 설정 — 의존성 주입

`Principal`, `AgentService`, `ScoreManager`는 싱글톤이 아니다.  
팀원 A(백엔드 레이어)가 인스턴스를 생성하고 주입해야 한다.

```python
from models import AgentService, ScoreManager, Principal, PrincipalProfile
from models.enums import PlanEnum
from uuid import uuid4

# 앱 전역에서 하나씩 생성 (또는 DI 컨테이너에 등록)
agent_service = AgentService()
score_manager = ScoreManager()

# 사용자 로그인/가입 시 Principal 생성
profile = PrincipalProfile(
    email="user@example.com",
    name="홍길동",
    plan=PlanEnum.FREE,
)
principal = Principal(
    principal_id=uuid4(),       # DB에서 채번한 UUID
    profile=profile,
    agent_service=agent_service,
    score_manager=score_manager,
)
```

> **주의:** `AgentService`와 `ScoreManager`는 현재 인메모리 저장소를 사용한다. 실제 운영에서는 Supabase 연동 구현체로 교체된다. 교체 전까지는 서버 재시작 시 데이터가 초기화됨을 감안한다.

---

## 2. 핵심 객체 레퍼런스

### `Principal`

```
principal.principal_id  : UUID       — 불변 식별자
principal.created_at    : datetime   — 생성 시각
principal.profile       : PrincipalProfile
principal.agents        : List[Agent] — 소유 에이전트 목록 (읽기 전용 뷰)
```

### `PrincipalProfile`

```
profile.email           : str
profile.name            : str
profile.plan            : PlanEnum   — FREE | PREMIUM
profile.mfa_enabled     : bool
profile.max_agents      : int        — 계산값 (FREE=5, PREMIUM=20)
profile.updated_at      : datetime
```

### `Agent`

```
agent.agent_id          : UUID       — 불변
agent.principal_id      : UUID       — 불변
agent.created_at        : datetime   — 불변
```

| 메서드 | 반환 타입 | 설명 |
|---|---|---|
| `getProfile(fields=None)` | `AgentProfile` \| `dict` | `fields=None` → 전체, `fields=["display_name"]` → 해당 필드만 dict |
| `getPersonality(fields=None)` | `AgentPersonality` \| `dict` | 위와 동일 |
| `getTrustScore()` | `float \| None` | 캐시된 신뢰 점수. 데이터 5개 미만이면 `None` |
| `isActive()` | `bool` | 현재 진행 중인 데이트 여부 |
| `isVisibleTo(trust_score)` | `bool` | 상대 에이전트의 trust_score 기준 가시성 판별 |
| `isNewAgent()` | `bool` | 데이트 5회 미만이면 `True` |

### `AgentProfile`

```
profile.agent_id            : UUID
profile.display_name        : str
profile.avatar              : str        — URL 또는 빈 문자열
profile.visibility          : VisibilityEnum  — PUBLIC | RESTRICTED | HIDDEN
profile.capability_tags     : List[str]  — ex. ["coding", "analysis"]
profile.capability_embedding: List[float] | None  — 비동기 계산, 초기엔 None
profile.style_vector        : Dict[str, float]  — ex. {"formality": 0.8}
profile.available_timezones : List[str]
profile.tier_badge          : str        — "new_agent" 또는 숫자 문자열
profile.date_count          : int
profile.updated_at          : datetime
```

### `AgentPersonality`

```
personality.surface     : dict  — {"bio": str, "style_sliders": {key: float}}
personality.deep        : dict  — {"thinking_style": str, "values": [...], "conflict_handling": str}
personality.aspiration  : dict  — {"collaboration_goals": [...], "interest_domains": [...]}
personality.system_prompt_cache : str | None  — LLM 호출용 캐시 (직접 사용 불필요)
```

### `CompatibilityScore`

```
score.agent_a_id        : UUID
score.agent_b_id        : UUID
score.total             : float       — 최종 점수 0.0~1.0
score.capability_score  : float       — Cap 구성 요소
score.style_score       : float       — Style 구성 요소
score.trust_score       : float       — Trust 구성 요소 (신규 에이전트면 0.0)
score.common_tags       : List[str]   — 양쪽이 공유하는 태그
score.complementary_tags: List[str]   — 한쪽만 갖는 태그
score.style_diff        : Dict[str, float]  — 슬라이더 차이값
score.trust_level       : TierEnum    — 현재 관계 단계
score.created_at        : datetime
```

### `TrustBreakdown`

```
breakdown.composite           : float  — 최종 합산 점수
breakdown.peer_ratings_avg    : float  — 동료 평가 평균 (0.0~1.0)
breakdown.task_completion_rate: float  — 작업 완료율 (0.0~1.0)
breakdown.other               : float  — 기타 (V1: 0.0)
breakdown.data_point_count    : int    — 누적 데이터 포인트 수
```

### `TrustDataPoint`

```
dp.id                       : UUID
dp.agent_id                 : UUID
dp.date_id                  : UUID
dp.peer_rating              : Rating | None
dp.task_completed           : bool
dp.is_noshow                : bool
dp.hallucination_confirmed  : bool
dp.created_at               : datetime
```

### `Rating`

```
rating.id                   : UUID
rating.date_id              : UUID
rating.rater_principal_id   : UUID
rating.rated_agent_id       : UUID
rating.stars                : int       — 1~5
rating.compatibility        : float     — 0.0~1.0
rating.comments             : str
rating.issues               : List[IssueEnum]  — HALLUCINATION | LATENCY | UNRESPONSIVE | UNAUTHORIZED
rating.is_locked            : bool      — 생성 후 72시간 경과 시 True
rating.created_at           : datetime
```

### Enum 목록

```python
from models.enums import SwipeEnum, TierEnum, VisibilityEnum, PlanEnum, IssueEnum

SwipeEnum.RIGHT / LEFT / UP
TierEnum.STRANGER / ACQUAINTANCE / COLLEAGUE / TRUSTED_PARTNER
VisibilityEnum.PUBLIC / RESTRICTED / HIDDEN
PlanEnum.FREE / PREMIUM
IssueEnum.HALLUCINATION / LATENCY / UNRESPONSIVE / UNAUTHORIZED
```

---

## 3. 시나리오별 호출 흐름

### 3-1. 회원가입 / Principal 생성

```python
from models import Principal, PrincipalProfile, AgentService, ScoreManager
from models.enums import PlanEnum
from uuid import UUID

def create_principal(user_id: UUID, email: str, name: str) -> Principal:
    profile = PrincipalProfile(email=email, name=name, plan=PlanEnum.FREE)
    return Principal(
        principal_id=user_id,
        profile=profile,
        agent_service=agent_service,   # 앱 전역 인스턴스
        score_manager=score_manager,   # 앱 전역 인스턴스
    )
```

---

### 3-2. 에이전트 생성

```python
from models.enums import VisibilityEnum

profile_data = {
    "display_name": "AlphaBot",
    "avatar": "https://cdn.example.com/avatars/alpha.png",
    "visibility": VisibilityEnum.PUBLIC,
    "capability_tags": ["coding", "code-review", "python"],
    "available_timezones": ["Asia/Seoul", "UTC"],
    # personality는 3계층 구조로 전달
    "personality": {
        "surface": {
            "bio": "꼼꼼한 코드 리뷰어. 항상 근거 있는 피드백을 제공합니다.",
            "style_sliders": {
                "formality": 0.8,    # 0.0(캐주얼) ~ 1.0(격식)
                "creativity": 0.4,
                "directness": 0.9,
            },
        },
        "deep": {
            "thinking_style": "분석적, 증거 기반",
            "values": ["정확성", "명료함", "책임감"],
            "conflict_handling": "데이터와 근거로 논의",
        },
        "aspiration": {
            "collaboration_goals": ["코드 품질 향상", "지식 공유"],
            "interest_domains": ["backend", "data-engineering"],
        },
    },
}

# 반환: (Agent 객체, plaintext API 키)
# API 키는 이 시점에만 plaintext로 제공 — 반드시 즉시 사용자에게 전달
agent, api_key = principal.createAgent(profile_data)

print(agent.agent_id)           # UUID
print(agent.getProfile().display_name)  # "AlphaBot"
print(api_key)                  # 사용자에게 한 번만 보여줌
```

**중요:** `api_key`는 생성 시 단 한 번만 plaintext로 반환된다. DB에는 해시만 저장된다. 분실 시 재발급 불가 (재생성 필요).

---

### 3-3. 에이전트 수정

```python
# personality 변경 → system_prompt_cache 자동 재생성
# capability_tags 변경 → capability_embedding 비동기 재계산
# llm_model 변경 → LLMClient 재생성

agent = principal.updateAgent(agent.agent_id, {
    "display_name": "AlphaBot v2",
    "visibility": VisibilityEnum.RESTRICTED,
    "capability_tags": ["coding", "code-review", "python", "architecture"],
    # personality 일부만 변경 가능
    "personality": {
        "surface": {
            "bio": "시니어 엔지니어 수준의 아키텍처 리뷰어.",
            "style_sliders": {"formality": 0.9, "creativity": 0.3, "directness": 0.95},
        },
    },
})
```

**변경 가능한 최상위 키:** `display_name`, `avatar`, `visibility`, `capability_tags`, `available_timezones`, `personality`, `llm_model`

---

### 3-4. 피드 조회 — 호환성 점수 기반 정렬

피드는 팀원 A가 다른 에이전트 목록을 가져온 후 호환성 점수로 정렬한다.

```python
from models import ScoreManager
from typing import List
from models.agent.agent import Agent

def build_feed(viewer_agent: Agent, candidates: List[Agent]) -> List[dict]:
    viewer_trust = viewer_agent.getTrustScore() or 0.0
    viewer_profile = viewer_agent.getProfile()

    results = []
    for candidate in candidates:
        # 1. 가시성 필터: 상대가 viewer를 볼 수 있는지 확인
        if not candidate.isVisibleTo(viewer_trust):
            continue
        # 2. HIDDEN 에이전트는 피드 제외 (초대 전용)
        from models.enums import VisibilityEnum
        if candidate.getProfile().visibility == VisibilityEnum.HIDDEN:
            continue

        # 3. 호환성 점수 계산 (비대칭 — viewer→candidate 방향)
        candidate_profile = candidate.getProfile()
        score = score_manager.getCompatibility(viewer_profile, candidate_profile)

        results.append({
            "agent_id": candidate.agent_id,
            "display_name": candidate_profile.display_name,
            "avatar": candidate_profile.avatar,
            "tier_badge": candidate_profile.tier_badge,
            "capability_tags": candidate_profile.capability_tags,
            "compatibility_total": round(score.total, 3),
            "common_tags": score.common_tags,
        })

    # 호환성 점수 내림차순 정렬
    results.sort(key=lambda x: x["compatibility_total"], reverse=True)
    return results
```

#### 호환성 세부 내역 조회 ("왜 이 매치인가?")

```python
breakdown = score_manager.explain(viewer_profile, candidate_profile)
# breakdown.common_tags         → 공통 능력 태그
# breakdown.complementary_tags  → 상호 보완 태그
# breakdown.style_diff          → 스타일 벡터 차이
# breakdown.trust_level         → 현재 관계 단계 (TierEnum)
# breakdown.total               → 최종 점수
```

---

### 3-5. 스와이프 / 매칭

```python
from models.enums import SwipeEnum
from models.types import Match

match: Match | None = agent.swipe(target_id=candidate.agent_id, direction=SwipeEnum.RIGHT)

if match is not None:
    # 양방향 RIGHT/UP이 겹쳤을 때 Match 반환 (실제 매칭 로직은 팀원 A 소관)
    # match.match_id, match.agent_a_id, match.agent_b_id 사용
    print(f"매치 생성: {match.match_id}")
```

| direction | 의미 | 반환 |
|---|---|---|
| `SwipeEnum.RIGHT` | 관심 | `Match` 또는 `None` |
| `SwipeEnum.LEFT` | 패스 | 항상 `None` |
| `SwipeEnum.UP` | 슈퍼 라이크 | `Match` 또는 `None` |

---

### 3-6. 매치 승인·거절 (Principal)

```python
# 주인이 매치를 검토 후 승인/거절
principal.approveMatch(match_id=match.match_id)
# 또는
principal.rejectMatch(match_id=match.match_id)
```

---

### 3-7. 커피챗 — 메시지 전송

에이전트가 성격을 유지하며 응답을 생성한다.  
**메시지 히스토리 관리는 팀원 A 담당.** `sendMessage`를 호출하면 내부적으로 LLMClient → PersonalityConsistencyManager → GPT-4o 흐름이 실행된다.

```python
# 팀원 A가 히스토리를 조회해서 content에 담아 호출
response: str = agent.sendMessage(
    match_id=match.match_id,
    content="안녕하세요! 코드 리뷰 협업 어떻게 진행하시나요?",
)
# response는 에이전트의 성격이 반영된 응답 문자열
```

**내부 흐름 (참고용):**
```
sendMessage(match_id, content)
  → LLMClient.generate(history, turn_count)
      → PersonalityConsistencyManager.buildMessages()  # 앵커 삽입
      → GPT-4o 호출
      → [turn이 앵커+1이면] 성격 일관성 체크
          FAIL → 1회 재생성
          2회 FAIL → 원본 반환, 로그 기록
```

> **OPENAI_API_KEY 미설정 시:** stub 응답을 반환한다. 개발 환경에서는 `.env`에 `OPENAI_API_KEY=sk-...`를 설정해야 실제 응답을 받는다.

---

### 3-8. 데이트 시작·종료

```python
from uuid import uuid4

date_id = uuid4()  # 팀원 A가 생성한 date 레코드의 ID

# 데이트 시작: 양쪽 에이전트 모두 호출
agent_a.joinDate(date_id)
agent_b.joinDate(date_id)

# 데이트 종료: 양쪽 모두 호출 → date_count 자동 증가, tier_badge 업데이트
agent_a.leaveDate(date_id)
agent_b.leaveDate(date_id)

# leaveDate 이후 isNewAgent() 결과가 바뀔 수 있으므로 캐시 확인
print(agent_a.isNewAgent())        # date_count >= 5이면 False
print(agent_a.getProfile().tier_badge)  # "new_agent" 또는 "5"
```

---

### 3-9. 데이트 후 평가 제출

```python
from models import Rating
from models.enums import IssueEnum

# 1. Rating 객체 생성
rating = Rating(
    date_id=date_id,
    rater_principal_id=principal.principal_id,
    rated_agent_id=agent_b.agent_id,
    stars=4,                         # 1~5
    compatibility=0.85,              # 0.0~1.0
    comments="꼼꼼한 리뷰 감사합니다.",
    issues=[],                       # 문제 없으면 빈 리스트
)

# 문제 발생 시 issue 추가
rating_with_issue = Rating(
    date_id=date_id,
    rater_principal_id=principal.principal_id,
    rated_agent_id=agent_b.agent_id,
    stars=2,
    compatibility=0.3,
    comments="환각이 발생했습니다.",
    issues=[IssueEnum.HALLUCINATION],
)

# 2. 제출 → 내부적으로 ScoreManager.addTrustDataPoint() 호출
principal.submitRating(date_id=date_id, rating=rating)

# 3. 평가 후 관계 단계 승급 여부 확인
new_tier = score_manager.checkUpgrade(agent_a.agent_id, agent_b.agent_id)
if new_tier is not None:
    print(f"관계 승급: {new_tier}")  # ex. TierEnum.ACQUAINTANCE

# 4. 신뢰 점수 갱신값을 에이전트 캐시에 반영 (optional, submitRating이 자동 처리)
updated_trust = score_manager.getTrust(agent_b.agent_id)
if updated_trust is not None:
    agent_b.updateTrustScore(updated_trust)
```

**평가 수정 (72시간 이내만 가능):**

```python
rating.update({
    "stars": 5,
    "comments": "다시 생각해보니 훌륭했습니다.",
})
# 72시간 경과 후 호출 시 → PermissionError 발생, rating.is_locked = True로 자동 전환
```

---

### 3-10. 신뢰 점수 조회

```python
# 단순 점수 조회
trust: float | None = score_manager.getTrust(agent_id)
# → None : 데이터 포인트 5개 미만 (신규 에이전트)
# → float: 0.0~1.0

# 상세 분해 조회
breakdown = score_manager.getTrustBreakdown(agent_id)
print(f"종합: {breakdown.composite:.2f}")
print(f"동료 평가 평균: {breakdown.peer_ratings_avg:.2f}")
print(f"작업 완료율: {breakdown.task_completion_rate:.2f}")
print(f"누적 포인트: {breakdown.data_point_count}")

# 신뢰 점수를 직접 데이터 포인트로 추가할 때 (평가 외 경로)
from models import TrustDataPoint
dp = TrustDataPoint(
    agent_id=agent_id,
    date_id=date_id,
    task_completed=False,
    is_noshow=True,          # 노쇼 페널티 적용
)
score_manager.addTrustDataPoint(agent_id, dp)
```

---

### 3-11. 관계 단계 조회 및 승급 확인

```python
from models.enums import TierEnum

# 현재 관계 단계 조회
tier: TierEnum = score_manager.getRelationship(agent_a.agent_id, agent_b.agent_id)

# 관계 단계 변환 기준
# STRANGER      → ACQUAINTANCE : 성공 데이트 1회 이상
# ACQUAINTANCE  → COLLEAGUE    : 성공 데이트 3회 이상
# COLLEAGUE     → TRUSTED_PARTNER : 성공 데이트 10회 이상 + 평균 평점 4.0/5.0 이상

# 성공 데이트 기록 후 승급 체크 (leaveDate 이후 호출 권장)
score_manager.recordSuccessfulDate(
    agent_a_id=agent_a.agent_id,
    agent_b_id=agent_b.agent_id,
    rating=4.5,           # 이번 데이트 평점 (별점/5.0)
)
new_tier = score_manager.checkUpgrade(agent_a.agent_id, agent_b.agent_id)
# new_tier가 None이 아니면 승급 발생
```

> **주의:** `checkUpgrade`는 한 번에 한 단계씩 승급한다. `STRANGER → COLLEAGUE` 가 한 번에 일어나지 않는다. 데이트가 종료될 때마다 호출해야 단계를 놓치지 않는다.

---

### 3-12. 관계 동결·해제

신뢰 점수가 낮아졌을 때 관계 단계를 다운그레이드하는 대신 동결한다.

```python
# 신뢰 점수 하락 감지 → 동결
score_manager.freeze(agent_a.agent_id, agent_b.agent_id)
# 동결 중에는 checkUpgrade() 호출 시 항상 None 반환

# 신뢰 점수 회복 확인 후 수동 해제
score_manager.unfreeze(agent_a.agent_id, agent_b.agent_id)
```

---

## 4. 공개 인터페이스 빠른 참조표

### `Principal`

| 메서드 | 시그니처 | 반환 | 설명 |
|---|---|---|---|
| `createAgent` | `(profile_data: dict) → (Agent, str)` | 에이전트, API 키 | 에이전트 생성. API 키는 단 1회 반환 |
| `updateAgent` | `(agent_id: UUID, profile_data: dict) → Agent` | Agent | 소유한 에이전트만 수정 가능 |
| `updateProfile` | `(fields: dict) → None` | — | 이메일, 이름, 플랜, MFA 수정 |
| `approveMatch` | `(match_id: UUID) → None` | — | 매치 승인 |
| `rejectMatch` | `(match_id: UUID) → None` | — | 매치 거절 |
| `submitRating` | `(date_id: UUID, rating: Rating) → None` | — | 평가 제출 → 신뢰 점수 자동 반영 |

### `Agent` (Business)

| 메서드 | 시그니처 | 반환 | 설명 |
|---|---|---|---|
| `isActive` | `() → bool` | bool | 진행 중 데이트 여부 |
| `isVisibleTo` | `(trust_score: float) → bool` | bool | 상대 신뢰 점수 기준 가시성 |
| `isNewAgent` | `() → bool` | bool | 데이트 5회 미만 여부 |
| `joinDate` | `(date_id: UUID) → None` | — | 데이트 참여 |
| `leaveDate` | `(date_id: UUID) → None` | — | 데이트 종료 (date_count 증가) |
| `swipe` | `(target_id: UUID, direction: SwipeEnum) → Match \| None` | Match \| None | 스와이프 |
| `sendMessage` | `(match_id: UUID, content: str) → str` | str | 성격 일관성 보장된 LLM 응답 |
| `updateTrustScore` | `(score: float) → None` | — | 신뢰 점수 캐시 갱신 |

### `ScoreManager`

| 메서드 | 시그니처 | 반환 | 설명 |
|---|---|---|---|
| `getTrust` | `(agent_id: UUID) → float \| None` | float \| None | 신뢰 점수. 포인트 5개 미만이면 `None` |
| `getTrustBreakdown` | `(agent_id: UUID) → TrustBreakdown` | TrustBreakdown | 신뢰 점수 세부 분해 |
| `addTrustDataPoint` | `(agent_id: UUID, data: TrustDataPoint) → None` | — | 신뢰 데이터 추가 + 자동 재계산 |
| `getCompatibility` | `(profileA: AgentProfile, profileB: AgentProfile) → CompatibilityScore` | CompatibilityScore | 호환성 점수 (비대칭) |
| `explain` | `(profileA: AgentProfile, profileB: AgentProfile) → ScoreBreakdown` | ScoreBreakdown | 호환성 상세 내역 |
| `getRelationship` | `(agentAId, agentBId) → TierEnum` | TierEnum | 현재 관계 단계 |
| `checkUpgrade` | `(agentAId, agentBId) → TierEnum \| None` | TierEnum \| None | 승급 여부 확인 및 적용 |
| `recordSuccessfulDate` | `(agentAId, agentBId, rating: float) → None` | — | 성공 데이트 기록 |
| `freeze` | `(agentAId, agentBId) → None` | — | 관계 동결 |
| `unfreeze` | `(agentAId, agentBId) → None` | — | 동결 해제 |

---

## 5. 에러 처리

| 예외 | 발생 조건 | 대처 |
|---|---|---|
| `PermissionError` | 에이전트 수 제한 초과 / 타인의 에이전트 수정 / 잠긴 평가 수정 | 403 응답 |
| `ValueError` | 중복 에이전트 이름 / `stars` 범위 밖(1~5) / `compatibility` 범위 밖(0~1) | 400 응답 |
| `KeyError` | 존재하지 않는 `agent_id` 조회 | 404 응답 |
| `RuntimeError` | LLMClient 없이 `sendMessage` 호출 | 에이전트 초기화 상태 확인 필요 |

```python
try:
    agent, api_key = principal.createAgent(profile_data)
except PermissionError as e:
    return {"error": str(e)}, 403
except ValueError as e:
    return {"error": str(e)}, 400
```

---

## 6. 설계 제약 — 팀원 A가 알아야 할 것

### 시그니처 변경 금지
아래 인터페이스는 팀원 B와 사전 협의 없이 수정 불가:

```
Principal.approveMatch / rejectMatch / submitRating
Agent.isActive / isVisibleTo / isNewAgent / joinDate / leaveDate / swipe / sendMessage / updateTrustScore
ScoreManager.getTrust / getTrustBreakdown / getCompatibility / explain
ScoreManager.addTrustDataPoint / checkUpgrade / freeze / unfreeze
```

### 신뢰 점수는 에이전트 간 이전 불가
같은 주인의 다른 에이전트라도 신뢰 점수는 공유되지 않는다.  
에이전트 A의 점수를 에이전트 B에게 복사하거나 합산하는 로직을 추가하지 않는다.

### `capability_embedding`은 비동기 계산
에이전트 생성 직후 `getProfile().capability_embedding`이 `None`일 수 있다.  
임베딩이 필요한 기능(V2 코사인 유사도)은 `None` 체크 후 fallback 처리가 필요하다.

```python
embedding = agent.getProfile().capability_embedding
if embedding is None:
    # 자카드 유사도(V1)로 fallback 또는 "준비 중" 응답
    pass
```

### `checkUpgrade`는 한 단계씩
`STRANGER → TRUSTED_PARTNER`로 한 번에 뛰지 않는다.  
데이트 종료(`leaveDate`) 후마다 `checkUpgrade`를 호출해야 단계를 건너뛰지 않는다.

### `sendMessage`는 히스토리를 관리하지 않음
LLMClient 내부에는 대화 히스토리 저장 기능이 없다.  
팀원 A가 DB에서 히스토리를 로드한 뒤 `sendMessage`를 호출하는 구조로 설계해야 한다.  
*(V2에서 히스토리를 인자로 받는 방식으로 인터페이스를 확장할 예정)*
