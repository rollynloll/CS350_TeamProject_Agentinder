# Match · DateSession · IMatchingService 설계 문서

**담당:** 팀원 B (신승운)  
**브랜치:** `feat/B`  
**관련 파일:** `models/types.py`, `models/date/`, `models/matching/`

---

## 개요

이 PR은 Agentinder의 핵심 AI 로직 세 가지를 구현한다.

| 클래스 | 위치 | 역할 |
|---|---|---|
| `Match` | `models/types.py` | 매치 로그 + 조회 헬퍼 |
| `DateSession` | `models/date/date_session.py` | 데이트 실행 단위 (handshake → date → rating) |
| `IMatchingService` | `models/matching/matching_service.py` | 팀원 A가 구현할 매칭 계약서 |

---

## 1. Match 변경사항

### 추가된 필드

```python
unmatched_at: Optional[datetime] = None  # None이면 활성 매치
```

### 추가된 헬퍼 메서드

```python
match.has_agent(agent_id: UUID) -> bool
match.other_agent_id(agent_id: UUID) -> UUID  # 상대방 ID 반환, 없으면 ValueError
```

### 설계 원칙

- 상태 머신 없음. `unmatched_at` 설정은 팀원 A(MatchHandler)가 담당한다.
- `has_agent` / `other_agent_id`는 DateHandler, FeedHandler에서 "이 매치에 내가 속하는가", "상대방이 누구인가"를 빠르게 조회하기 위한 편의 메서드다.

---

## 2. DateSession

### 생성자

```python
DateSession(
    agent_a: Agent,
    agent_b: Agent,
    match_id: UUID,
    skip_trust_check: bool,       # True=비동기, False=동기
    topic: Optional[str],         # None이면 IcebreakerGenerator 자동 생성
    score_manager: ScoreManager,
    min_trust_threshold: float = 0.3,
    max_turns_per_agent: int = 20,
)
```

### run() 실행 흐름

```
handshake() ──── 실패(CANCELLED) ────► DateResult(ratings=[], transcript=[])
    │
    ▼ 성공(IN_PROGRESS)
 date()  ──────── 실패(NO_SHOW) ─────► DateResult + _record_noshow()
    │
    ▼ 성공
 rating() ──────────────────────────► DateResult(COMPLETED)
```

### 단계별 동작

#### handshake()

| `skip_trust_check` | 동작 |
|---|---|
| `True` (비동기) | 신뢰 점수 조회 없이 즉시 IN_PROGRESS |
| `False` (동기) | 양쪽 getTrust() 조회. `None`(신규 에이전트)은 면제. 점수 있으나 임계값 미만이면 CANCELLED |

신규 에이전트(`getTrust() == None`)를 면제하는 이유: 데이터가 없어서 신뢰 점수를 모르는 것이지, 신뢰할 수 없다는 의미가 아니기 때문이다.

#### date()

- `topic`이 `None`이면 `IcebreakerGenerator`가 공통 태그 기반 주제를 자동 생성한다.
- 두 에이전트가 `max_turns_per_agent` 라운드씩 번갈아 응답한다.
- 각 턴마다 `LLMClient.generate(history, turn_count)`에 **누적 transcript를 포함한 전체 히스토리**를 전달한다.
- LLMClient가 없거나 예외가 발생하면 `NO_SHOW`로 처리한다.
- REQ-0308: 한쪽이 전체 턴의 80% 이상 전송하면 `is_imbalanced=True`로 기록한다.

#### rating()

transcript 길이를 기준으로 outcome을 결정한다.

| 완주율 | outcome | stars |
|---|---|---|
| ≥ 80% | SUCCESSFUL | 5 |
| 40% ~ 80% | NEUTRAL | 3 |
| < 40% | UNSUCCESSFUL | 1 |

**동기 매칭** (`skip_trust_check=False`):
- `Rating` 1개: `agent_a.principal_id`가 `agent_b`를 평가
- `TrustDataPoint`: 양쪽 모두 추가 (`agent_b`에만 `peer_rating` 포함)

**비동기 매칭** (`skip_trust_check=True`):
- `Rating` 2개: 각자 상대를 자동 평가
- `TrustDataPoint`: 양쪽 모두 `peer_rating` 포함하여 추가

rating() 이후 `ScoreManager.checkUpgrade()`를 호출해 관계 승급 여부를 자동 반영한다.

**NO_SHOW 발생 시**: 양쪽 모두에 `is_noshow=True` TrustDataPoint를 추가한다.

### DateResult

```python
@dataclass
class DateResult:
    outcome: DateOutcome          # SUCCESSFUL / NEUTRAL / UNSUCCESSFUL
    ratings: List[Rating]         # 동기=1개, 비동기=2개, 실패=0개
    transcript: List[Message]
    trust_delta: float            # agent_a 신뢰 점수 변화량
    status: DateStatus
    is_imbalanced: bool = False
```

> **팀원 A에게**: `run()` 이후 `DateResult.ratings`를 순회하며 DB에 저장하고, `transcript`를 TranscriptService에 전달하면 된다.

---

## 3. IMatchingService

팀원 B가 인터페이스를 정의하고, **팀원 A가 구현한다.**

```python
class IMatchingService(ABC):

    @abstractmethod
    def runAsyncMatch(self, agent_id: UUID) -> DateSession:
        # 비동기. 랜덤 PUBLIC 에이전트, skipTrustCheck=True, topic=None
        # 항상 DateSession 반환 (None 없음)

    @abstractmethod
    def runAiMatch(self, agent_id: UUID, topic: str) -> Optional[DateSession]:
        # 동기. 호환성 최고점 PUBLIC 에이전트, skipTrustCheck=False
        # 적합한 상대 없으면 None

    @abstractmethod
    def runSelectMatch(
        self,
        agent_id: UUID,
        target_id: UUID,
        action: SwipeEnum,
        topic: str,
    ) -> Optional[DateSession]:
        # 동기. 직접 선택, mutual swipe 확인, skipTrustCheck=False
        # mutual 아니면 None
```

### 팀원 A 구현 가이드

세 메서드 모두 상대가 결정되면 내부에서 아래 순서로 처리한다:

```python
# 1. Match 레코드 DB INSERT
match_id = db.insert_match(agent_a_id, agent_b_id)

# 2. DateSession 생성 후 반환
return DateSession(
    agent_a=agent_a,
    agent_b=agent_b,
    match_id=match_id,
    skip_trust_check=skip_trust_check,
    topic=topic,
    score_manager=score_manager,
)
# run()은 DateHandler가 호출한다 — IMatchingService는 생성만 담당
```

---

## 4. IcebreakerGenerator

`topic=None`(비동기 매칭)일 때 `date()` 내부에서 자동 호출된다.

```python
IcebreakerGenerator().generate(agent_a, agent_b) -> str
```

- 공통 capability_tag가 있으면 해당 태그를 주제로 사용
- 공통 태그 없으면 전체 태그 합집합에서 첫 번째 선택
- 태그가 아예 없으면 일반적인 협업 주제 반환

---

## 5. 파일 구조

```
models/
├── types.py                      # Match 보강 (unmatched_at, has_agent, other_agent_id)
├── date/
│   ├── __init__.py
│   └── date_session.py           # DateSession, DateResult, DateStatus, DateOutcome, IcebreakerGenerator
├── matching/
│   ├── __init__.py
│   └── matching_service.py       # IMatchingService (ABC)
└── tests/
    └── test_date_session.py      # 31개 테스트 (전원 통과)
```

---

## 6. 테스트 커버리지

| 영역 | 테스트 수 |
|---|---|
| Match 헬퍼 | 7 |
| IcebreakerGenerator | 3 |
| handshake (신뢰 체크) | 4 |
| date (대화 루프) | 5 |
| rating (점수 반영) | 8 |
| outcome 임계값 | 3 |
| **합계** | **31** |
