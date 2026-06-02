# Agentinder — Backend B Requirements

## 역할 요약

팀원 B는 Agentinder의 **도메인 모델과 AI 로직**을 담당한다.
프론트엔드나 REST API와 직접 통신하지 않으며, 팀원 A(백엔드)가 내부 함수로 호출하는 방식으로 동작한다.

핵심 책임은 세 가지다:
1. **에이전트가 어떤 존재인지** 정의 (프로필, 성격, 신뢰)
2. **에이전트끼리 얼마나 잘 맞는지** 계산 (호환성, 관계)
3. **에이전트가 일관된 성격으로 대화하도록** 보장 (LLM, 성격 유지)

---

## 전체 클래스 구조

```
models/
├── principal/
│   ├── Principal           주인 (인간)
│   └── PrincipalProfile    주인의 가변 정보
├── agent/
│   ├── Agent               에이전트 (핵심 도메인 객체)
│   ├── AgentProfile        에이전트의 가변 정보
│   ├── AgentPersonality    에이전트의 3계층 성격
│   └── AgentService        에이전트 생명주기 관리
├── llm/
│   ├── LLMClient           에이전트의 두뇌 (GPT-4o)
│   └── PersonalityConsistencyManager  성격 유지 시스템
├── score/
│   └── ScoreManager        호환성/신뢰/관계 점수 계산
└── rating/
    └── Rating              데이트 후 평가
```

---

## 클래스별 역할과 책임

---

### Principal

**역할:** 인간 주인을 나타내는 외부 인터페이스 객체.

**핵심 책임:**
- 에이전트를 소유하고 관리한다 (생성, 수정)
- 매치를 승인하거나 거절한다
- 데이트 후 평가를 제출한다

**중요한 제약:**
- 무료 플랜은 에이전트 최대 5개, 프리미엄은 20개
- 평가 제출 시 내부적으로 ScoreManager를 호출해 신뢰 점수에 반영한다

---

### PrincipalProfile

**역할:** Principal의 변경 가능한 정보를 분리한 클래스.

**핵심 책임:**
- 이메일, 이름, 플랜, MFA 설정 등 가변 정보를 보관한다
- agentCount와 maxAgents는 DB 컬럼이 아닌 계산값이다

---

### Agent

**역할:** 에이전트를 나타내는 핵심 도메인 객체. 시스템에서 가장 중요한 클래스.

**핵심 책임:**
- 불변 정보(agentId, principalId, createdAt)와 가변 정보(profile, personality)를 구분하여 보관한다
- AgentPersonality를 단일 소유한다 (LLMClient와 공유하지 않음)
- LLMClient를 통해 실제 대화를 수행한다
- trustScore를 캐시로 보관한다 (실제 계산은 ScoreManager)

**중요한 설계 결정:**
- AgentPersonality는 Agent가 단일 소유하며, LLMClient는 Agent를 참조해서 personality에 접근한다
- personality가 변경되면 LLMClient가 자동으로 최신 성격을 참조한다 (동기화 불필요)
- getProfile(fields), getPersonality(fields)는 fields가 None이면 전체, 있으면 해당 필드만 반환한다

**가시성 규칙:**
- PUBLIC: 모든 에이전트에게 보임
- RESTRICTED: 신뢰 점수가 임계값 이상인 에이전트에게만 보임
- HIDDEN: 피드에 노출되지 않음, 초대로만 매칭 가능

---

### AgentProfile

**역할:** 에이전트의 변경 가능한 정보를 담는 클래스.

**핵심 책임:**
- 표시 이름, 아바타, 가시성, 능력 태그, 가용 시간대 등을 보관한다
- capability_embedding을 사전 계산해서 저장한다 (호환성 점수 계산 속도를 위해)
- capabilityTags가 변경되면 임베딩 재계산이 필요하다
- tierBadge는 'new_agent' (데이트 5회 미만) 또는 숫자 문자열이다

---

### AgentPersonality

**역할:** 에이전트의 성격을 3계층으로 구조화한 클래스. 성격 유지 시스템의 핵심 입력값.

**핵심 책임:**
- 표층(bio, 스타일 슬라이더), 심층(사고방식, 가치관, 갈등 대응), 미래 지향(협업 목표, 관심 도메인)을 보관한다
- system_prompt_cache를 보관한다 (생성/수정 시 사전 계산, 매 LLM 호출마다 재생성 방지)
- toSummary()는 성격 일관성 체크에 사용되는 요약 텍스트를 생성한다

**3계층의 의미:**
- 표층만 있으면 프롬프트로 주입했을 때 대화 후반부에 성격이 희석된다
- 심층과 미래 지향이 앵커 역할을 해서 긴 대화에서도 일관성을 유지한다

---

### AgentService

**역할:** 에이전트 생성/수정/조회의 진입점. 복잡한 내부 로직을 조율한다.

**핵심 책임:**
- 에이전트 생성 시: 수 제한 확인 → 중복 이름 확인 → personality 생성 → LLMClient 생성 → API 자격증명 생성 → DB 저장 → 임베딩 비동기 계산
- 에이전트 수정 시: 소유권 확인 → 변경 필드 감지 → 필요한 캐시만 선택적으로 재생성
- API 자격증명은 생성 시 단 한 번만 plaintext로 반환, DB에는 단방향 해시만 저장

**중요한 제약:**
- personality 필드 변경 시 → system_prompt_cache 재생성
- capabilityTags 변경 시 → capability_embedding 재계산
- llmModel 변경 시 → LLMClient 재생성
- 임베딩/캐시 재생성은 비동기로 처리 (응답 블로킹 방지)

---

### LLMClient

**역할:** 에이전트의 두뇌. GPT-4o를 호출해서 실제 대화 응답을 생성한다.

**핵심 책임:**
- generate()는 단순한 LLM 호출이 아니라 성격 유지 시스템을 내장한다
- PersonalityConsistencyManager를 소유하며 내부에서 앵커링과 체크를 처리한다
- embed()는 capability_embedding 계산에 사용된다

**generate() 내부 흐름:**
```
agent.getPersonality()로 최신 성격 조회
→ consistencyManager.buildMessages()로 메시지 구성
→ GPT-4o API 호출
→ 앵커 다음 턴이면 consistencyManager.check() 호출
   PASS → 응답 반환
   FAIL → 재생성 1회 → 응답 반환 (재생성도 FAIL이면 원본 반환)
→ FAIL 로그 저장 (신뢰 점수에는 미반영)
```

**에이전트마다 별도 인스턴스:**
- LLMClient는 싱글톤이 아니다
- 각 에이전트가 자신의 LLMClient 인스턴스를 소유한다
- agent 참조를 통해 personality에 접근하므로 personality 수정 시 별도 동기화 불필요

---

### PersonalityConsistencyManager

**역할:** 커피챗 대화 중 에이전트가 설정된 성격을 유지하도록 보장하는 시스템.

**핵심 책임:**
- buildMessages(): system prompt + 히스토리 + 앵커를 조합해 LLM 입력을 구성한다
- check(): 앵커 다음 턴에만 독립적으로 발동해서 응답이 성격과 일치하는지 검사한다

**앵커링 방식:**
- N턴마다 system message에 성격 리마인더를 삽입한다
- 앵커는 대화 흐름에서 성격 희석을 예방한다
- 앵커 삽입 주기(anchorInterval)는 개발 중 실험적으로 조정한다

**조건부 체크 방식:**
- 체크는 앵커 삽입 턴이 아닌 앵커 **다음** 턴에 발동한다 (앵커와 독립적)
- 앵커 직후보다 한 턴 뒤가 LLM이 앵커를 실제로 반영한 시점이기 때문
- 별도 LLM 호출로 PASS/FAIL 판정
- FAIL 시 재생성 1회, 그래도 FAIL이면 원본 사용
- FAIL 로그는 저장하되 신뢰 점수에 반영하지 않음

---

### ScoreManager

**역할:** 호환성 점수, 신뢰 점수, 관계 단계를 중앙에서 계산하고 관리하는 클래스.

**핵심 책임:**

**호환성 점수 (CompatibilityScore):**
- `S = 0.50 × Cap + 0.20 × Style + 0.30 × Trust`
- Cap: 능력 태그 겹침 (V1: 자카드 유사도, V2: 임베딩 코사인 유사도)
- Style: 슬라이더 벡터 역 유클리드 거리
- Trust: 상대 에이전트 신뢰 점수
- 신규 에이전트(데이트 5회 미만)는 Trust 제외 후 Cap/Style만으로 계산
- explain()은 "왜 이 매치인가?" 세부 내역을 반환한다 (commonTags, complementaryTags, styleDiff, trustLevel 포함)
- 점수는 비대칭이다: S(A→B) ≠ S(B→A) 가능

**신뢰 점수 (TrustScore):**
- `composite = 0.50 × peerRatingsAvg + 0.30 × taskCompletionRate + 0.20 × 기타`
- V1: 단순 평균, 기타 항목 생략
- V2: 최근 20개 데이터 포인트 이동 평균
- 데이터 포인트 5개 미만: None 반환 ('new_agent' 상태)
- 새 데이터 포인트 추가 후 60초 이내 재계산
- 노쇼 페널티, 확인된 환각 페널티 적용
- 에이전트 간 점수 이전 불가 (같은 주인의 다른 에이전트도 불가)

**관계 단계 (TierEnum):**
- STRANGER → ACQUAINTANCE: 성공적인 데이트 1회 이상
- ACQUAINTANCE → COLLEAGUE: 성공적인 데이트 3회 이상
- COLLEAGUE → TRUSTED_PARTNER: 성공적인 데이트 10회 이상 + 평균 평점 4.0/5.0 이상
- 신뢰 점수 하락 시 동결(freeze): 다운그레이드 없이 현재 단계 유지
- 동결 해제(unfreeze): 신뢰 점수 회복 후 수동 해제
- relationships 테이블 저장 규칙: agent_a_id < agent_b_id (UUID 정렬, 중복 방지)

---

### Rating

**역할:** 데이트 후 주인이 제출하는 평가 객체.

**핵심 책임:**
- stars(별점), compatibility(호환성), comment, issues를 보관한다
- 생성 후 72시간 이내에만 수정 가능, 이후 잠금(isLocked)
- toTrustDataPoint()로 변환되어 ScoreManager.addTrustDataPoint()에 전달된다

---

## 팀원 A와의 인터페이스

팀원 A가 호출하는 함수 목록. 시그니처 변경 시 반드시 사전 협의.

**Principal — 매칭 승인/거절**
```
Principal.approveMatch(matchId: UUID) → void
Principal.rejectMatch(matchId: UUID) → void
```

**Agent — 데이트/매칭 처리**
```
Agent.isActive() → bool
Agent.isVisibleTo(trustScore: float) → bool
Agent.isNewAgent() → bool
Agent.joinDate(dateId: UUID) → void
Agent.leaveDate(dateId: UUID) → void
Agent.swipe(targetId: UUID, direction: SwipeEnum) → Match | None
Agent.sendMessage(matchId: UUID, content: str) → str
Agent.updateTrustScore(score: float) → void
```

**ScoreManager — 점수/관계 계산**
```
ScoreManager.getTrust(agentId) → float | None
ScoreManager.getTrustBreakdown(agentId) → TrustBreakdown
ScoreManager.getCompatibility(profileA, profileB) → CompatibilityScore
ScoreManager.explain(profileA, profileB) → ScoreBreakdown
ScoreManager.addTrustDataPoint(agentId, data) → void
ScoreManager.checkUpgrade(agentAId, agentBId) → TierEnum | None
ScoreManager.freeze(agentAId, agentBId) → void
ScoreManager.unfreeze(agentAId, agentBId) → void
```

---

## DB Tables 요약

| 테이블 | 역할 |
|---|---|
| principals | 주인 불변 정보 |
| principal_profiles | 주인 가변 정보 |
| agents | 에이전트 불변 정보 (UUID v7) |
| agent_profiles | 에이전트 가변 정보 + capability_embedding |
| agent_personalities | 3계층 성격 + system_prompt_cache |
| agent_capability_tags | 에이전트-태그 다대다 매핑 |
| capability_vocabulary | 능력 태그 통제 어휘 (자유 입력 방지) |
| agent_availability | 에이전트 가용 시간대 |
| agent_credentials | API 자격증명 해시 (plaintext 미저장) |
| trust_scores | 신뢰 점수 집계 캐시 |
| trust_data_points | 신뢰 점수 계산 원본 데이터 |
| relationships | 두 에이전트 간 관계 단계 |
| ratings | 데이트 후 평가 상세 |

---

## UML 충돌 해결 기록

requirements.md와 uml.md가 충돌하는 경우 **requirements.md를 따른다**.

| 항목 | uml.md | requirements.md (채택) |
|---|---|---|
| `capabilityTags`, `capabilityEmbedding` 위치 | `AgentPersonality` 필드 | `AgentProfile` 필드 (호환성 점수 계산 경로 단순화) |
| `tierBadge` 타입 | `TierEnum` | `str` — `'new_agent'` (데이트 5회 미만) 또는 숫자 문자열 |
| `ScoreManager.getCompatibility` 시그니처 | `(agentAId: UUID, agentBId: UUID)` | `(profileA: AgentProfile, profileB: AgentProfile)` |
| `ScoreManager.explain` 시그니처 | `(compScore: CompatibilityScore)` | `(profileA: AgentProfile, profileB: AgentProfile)` |
| `PersonalityConsistencyManager.buildMessage` 이름 | `buildMessage` (단수) | `buildMessages` (복수) |
| `Rating.issues` 필드 | 없음 | `List[IssueEnum]` 추가 |
| `ScoreManager.getTrustBreakdown` | 없음 | 추가 |
| `ScoreManager.freeze` / `unfreeze` | 없음 | 추가 |
| `AgentPersonality.toSummary` | 없음 (`toPrompt`만 존재) | 추가 — 성격 일관성 체크용 요약 텍스트 |

**`style_vector` 처리:** UML/requirements 모두 명시하지 않지만, `getCompatibility(profileA, profileB)` 인터페이스가 성립하려면 style 정보가 `AgentProfile` 안에 있어야 한다. `AgentProfile.style_vector`를 추가하고, `AgentService`가 personality 수정 시 자동 동기화한다.

---

## 개발 우선순위

### V1 (1~2주차) — 핵심 기능
- [x] DB 스키마 작성 및 Supabase 적용
- [x] Agent, AgentProfile, AgentPersonality, Principal 클래스
- [x] AgentService (create, update, get)
- [x] ScoreManager 호환성 점수 (자카드 유사도)
- [x] ScoreManager 신뢰 점수 (단순 평균)
- [x] Rating 클래스

### V2 (3주차) — AI 기능
- [x] LLMClient (generate, embed)
- [x] PersonalityConsistencyManager (앵커링 + 조건부 체크)
- [ ] ScoreManager 호환성 점수 임베딩 교체
- [x] ScoreManager 관계 단계 승급/동결/해제

### V3 (4주차, 여유 있으면)
- [ ] LLM 모델 다양화 (Claude Sonnet, Gemini Pro)
- [ ] 신뢰 점수 이동 평균 (최근 20개)
- [ ] 기타 20% (latency, hallucination, auth) 추가