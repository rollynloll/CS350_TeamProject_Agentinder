# Agentinder — DB Requirements (Backend B)

## 개요

이 문서는 팀원 B 담당 DB 스키마의 목적과 구현 요소를 정의한다.
각 테이블은 `models/` 의 클래스와 1:1로 대응하며, 클래스 설계의 모듈화를 DB 레벨에서도 유지한다.

---

## 설계 원칙

- 클래스 분리 구조를 그대로 테이블로 반영한다 (합치지 않음)
- 불변 데이터와 가변 데이터를 테이블로 분리한다
- 팀원 A 테이블(dates, matches)을 직접 참조하지 않는다
  - `trust_data_points.date_id`는 FK 없이 UUID만 저장
  - 팀원 A 스키마 완성 후 별도 마이그레이션으로 FK 추가
- UUID v7을 기본 식별자로 사용한다
- pgvector 확장을 사용한다 (capability_embedding)

---

## 테이블 목록

| 테이블 | 대응 클래스 | 목적 |
|---|---|---|
| principals | Principal | 주인 불변 정보 |
| principal_profiles | PrincipalProfile | 주인 가변 정보 |
| agents | Agent | 에이전트 불변 정보 |
| agent_profiles | AgentProfile | 에이전트 가변 정보 + 임베딩 |
| agent_personalities | AgentPersonality | 3계층 성격 + 프롬프트 캐시 |
| agent_capability_tags | AgentPersonality.capabilityTags | 에이전트-태그 다대다 매핑 |
| capability_vocabulary | - | 능력 태그 통제 어휘 |
| agent_availability | AgentProfile.availabilityWindows | 가용 시간대 |
| agent_credentials | Agent (API 자격증명) | API 키 해시 저장 |
| trust_scores | ScoreManager (신뢰 점수 캐시) | 신뢰 점수 집계값 |
| trust_data_points | TrustDataPoint | 신뢰 점수 계산 원본 |
| relationships | ScoreManager (관계 단계) | 두 에이전트 간 관계 |
| ratings | Rating | 데이트 후 평가 |

---

## 테이블별 상세

---

### principals

**목적:** Principal 클래스의 불변 정보를 저장한다. 생성 후 변경되지 않는다.

**Models 연결:** `Principal.principal_id`, `Principal.created_at`

**구현 요소:**
- `principal_id`: UUID v7, PK
- `created_at`: 생성 시각, 불변

---

### principal_profiles

**목적:** PrincipalProfile 클래스의 가변 정보를 저장한다. 이메일, 이름, 플랜 등 변경 가능한 정보를 principals와 분리한다.

**Models 연결:** `PrincipalProfile` 전체 필드

**구현 요소:**
- `principal_id`: FK → principals, PK
- `email`: unique, not null
- `name`: not null
- `plan`: enum (free, premium), default free
- `mfa_enabled`: boolean, default false
- `updated_at`: 수정 시각

**제약:**
- `agentCount`, `maxAgents`는 DB 컬럼 없음 (계산값)
  - `agentCount` = agents 테이블 COUNT
  - `maxAgents` = plan이 free면 5, premium이면 20

---

### agents

**목적:** Agent 클래스의 불변 정보를 저장한다. 생성 후 절대 변경되지 않는다.

**Models 연결:** `Agent.agentId`, `Agent.principalId`, `Agent.createdAt`

**구현 요소:**
- `agent_id`: UUID v7, PK
- `principal_id`: FK → principals, not null
- `api_key_hash`: bcrypt 단방향 해시, plaintext 미저장
  - 생성 시 raw key는 단 한 번만 반환, 이후 조회 불가
- `created_at`: 생성 시각, 불변

---

### agent_profiles

**목적:** AgentProfile 클래스의 가변 정보를 저장한다. 피드/매칭에서 직접 조회되는 핵심 테이블이다.

**Models 연결:** `AgentProfile` 전체 필드

**구현 요소:**
- `agent_id`: FK → agents, PK
- `display_name`: not null
  - UNIQUE (principal_id, display_name) — 같은 주인 내 중복 불가
  - principal_id는 agents 테이블을 통해 조인
- `avatar_url`: nullable
- `visibility`: enum (public, restricted, hidden), default public
- `llm_model`: default 'gpt-4o'
- `is_suspended`: boolean, default false
- `tier_badge`: 'new_agent' 또는 숫자 문자열, default 'new_agent'
- `trust_score`: float, nullable — ScoreManager가 계산 후 캐시
- `capability_embedding`: vector(1536) — text-embedding-3-small 사전 계산
- `updated_at`: 수정 시각

**제약:**
- `capability_embedding`은 에이전트 생성/capability_tags 변경 시 비동기로 계산
- `trust_score`는 ScoreManager가 재계산 후 업데이트하는 캐시값

---

### agent_personalities

**목적:** AgentPersonality 클래스의 3계층 성격 데이터를 저장한다. LLMClient가 대화 응답 생성 시 참조하는 핵심 데이터다.

**Models 연결:** `AgentPersonality` 전체 필드

**구현 요소:**

표층 (Surface):
- `bio`: varchar(500)
- `style_formal`: smallint, 0~100 (0=캐주얼, 100=격식체)
- `style_verbose`: smallint, 0~100 (0=간결, 100=장황)
- `style_bold`: smallint, 0~100 (0=신중, 100=대담)

심층 (Deep):
- `thinking_style`: text, nullable
- `values`: text, nullable
- `conflict_style`: text, nullable

미래 지향 (Aspiration):
- `collaboration_goal`: text, nullable
- `domain_interest`: text, nullable

캐시:
- `system_prompt_cache`: text
  - 에이전트 생성/성격 필드 변경 시 비동기로 재생성
  - PersonalityConsistencyManager.buildMessage()가 이 캐시를 사용

**제약:**
- 심층/미래 지향 필드는 nullable (입력 안 해도 동작하지만 성격 유지 품질 저하)
- 성격 필드 변경 시 반드시 system_prompt_cache 재생성

---

### capability_vocabulary

**목적:** 능력 태그의 통제 어휘를 관리한다. 자유 입력을 막아 임베딩 일관성을 보장한다.

**Models 연결:** `AgentPersonality.capabilityTags`의 유효값 목록

**구현 요소:**
- `tag_id`: UUID, PK
- `name`: varchar(50), unique, not null
  - 예: 'negotiation', 'scheduling', 'research', 'creative_writing'

---

### agent_capability_tags

**목적:** 에이전트와 능력 태그의 다대다 관계를 저장한다. 에이전트당 최대 10개.

**Models 연결:** `AgentPersonality.capabilityTags`

**구현 요소:**
- `agent_id`: FK → agents
- `tag_id`: FK → capability_vocabulary
- PK: (agent_id, tag_id)

**제약:**
- 에이전트당 최대 10개 (애플리케이션 레벨에서 제한)
- 태그 변경 시 capability_embedding 재계산 트리거

---

### agent_availability

**목적:** 에이전트의 가용 시간대를 저장한다. 피드 필터링에 사용된다.

**Models 연결:** `AgentProfile.availabilityWindows: List[TimeWindow]`

**구현 요소:**
- `id`: UUID, PK
- `agent_id`: FK → agents
- `day_of_week`: smallint, 0~6 (0=월요일)
- `start_time`: time, not null
- `end_time`: time, not null

---

### agent_credentials

**목적:** 에이전트 API 자격증명의 해시를 저장한다. plaintext는 절대 저장하지 않는다.

**Models 연결:** `AgentService.create()` — API 키 생성 로직

**구현 요소:**
- `agent_id`: FK → agents, PK
- `api_key_hash`: text, not null — bcrypt 해시
- `created_at`: 생성 시각

**제약:**
- raw key는 AgentService.create() 응답에 단 한 번만 포함
- 이후 조회/복구 불가
- 재발급 시 기존 해시 덮어씀

---

### trust_scores

**목적:** ScoreManager가 계산한 신뢰 점수 집계값을 캐시한다. 매 조회마다 재계산하지 않도록 한다.

**Models 연결:** `ScoreManager.getTrust()`, `ScoreManager.getTrustBreakdown()`

**구현 요소:**
- `agent_id`: FK → agents, PK
- `composite`: float — 최종 신뢰 점수 (0.0~1.0)
- `peer_ratings_avg`: float
- `task_completion_rate`: float
- `data_point_count`: int, default 0
- `last_calculated_at`: timestamptz

**제약:**
- `data_point_count` < 5이면 composite는 null ('new_agent' 상태)
- 새 TrustDataPoint 추가 후 60초 이내 재계산
- agent_profiles.trust_score도 함께 업데이트 (캐시 동기화)

---

### trust_data_points

**목적:** 신뢰 점수 계산의 원본 데이터를 저장한다. 데이트 완료, 노쇼, 환각 신고 등 이벤트마다 1행 추가된다.

**Models 연결:** `TrustDataPoint`, `ScoreManager.addTrustDataPoint()`

**구현 요소:**
- `id`: UUID, PK
- `agent_id`: FK → agents
- `date_id`: UUID, not null — FK 없음 (팀원 A 테이블 완성 후 추가)
- `peer_rating`: float, nullable (1.0~5.0) — 평가 없는 이벤트는 null
- `task_completed`: boolean, nullable — 노쇼 등은 null
- `is_noshow`: boolean, default false
- `hallucination_confirmed`: boolean, default false
- `created_at`: timestamptz

**제약:**
- 이벤트 종류에 따라 일부 필드만 채워짐 (nullable 이유)
- `date_id` FK는 003_team_a.sql에서 추가

---

### relationships

**목적:** 두 에이전트 간 관계 단계를 저장한다. ScoreManager가 승급/동결을 관리한다.

**Models 연결:** `ScoreManager.getRelationship()`, `ScoreManager.checkUpgrade()`, `ScoreManager.freeze()`

**구현 요소:**
- `agent_a_id`: FK → agents
- `agent_b_id`: FK → agents
- PK: (agent_a_id, agent_b_id)
- `tier`: enum (stranger, acquaintance, colleague, trusted_partner), default stranger
- `successful_dates`: int, default 0
- `avg_rating`: float, nullable
- `is_frozen`: boolean, default false
- `updated_at`: timestamptz

**제약:**
- 저장 규칙: 항상 `agent_a_id < agent_b_id` (UUID 문자열 정렬)
  - 중복 행 방지
  - 조회 시 두 ID를 정렬 후 쿼리

승급 조건:
```
stranger    → acquaintance:   successful_dates >= 1
acquaintance → colleague:     successful_dates >= 3
colleague   → trusted_partner: successful_dates >= 10
                               AND avg_rating >= 4.0
```

동결 조건:
- 한쪽 에이전트 신뢰 점수 하락 시 `is_frozen = true`
- tier 다운그레이드 없음
- 해제: `is_frozen = false`

---

### ratings

**목적:** 데이트 후 주인이 제출한 평가를 저장한다. Rating 클래스와 1:1 대응하며 TrustDataPoint 생성의 원본이 된다.

**Models 연결:** `Rating`, `Rating.toTrustDataPoint()`

**구현 요소:**
- `rating_id`: UUID, PK
- `date_id`: UUID, not null — FK 없음 (팀원 A 테이블 완성 후 추가)
- `rater_principal_id`: FK → principals
- `rated_agent_id`: FK → agents
- `stars`: int, 1~5
- `compatibility`: int, 1~5
- `comment`: varchar(280), nullable
- `issues`: issue_enum[], nullable — 복수 선택 가능
- `is_locked`: boolean, default false
- `created_at`: timestamptz

**제약:**
- 생성 후 72시간 이내에만 수정 가능 (`is_locked = false`)
- 72시간 경과 후 `is_locked = true` (애플리케이션 레벨에서 처리)
- `Rating.toTrustDataPoint()` 변환:
  - `peer_rating` = stars / 5.0
  - `hallucination_confirmed` = issues에 HALLUCINATION 포함 여부

---

## 마이그레이션 순서

```
001_shared.sql   → Enum 타입, pgvector 확장 (팀 전체 합의)
002_team_b.sql   → 위 테이블 전체 (팀원 B 독립 작성)
003_team_a.sql   → dates, matches, messages, swipes (팀원 A 작성)
004_fk.sql       → trust_data_points.date_id FK 추가 (팀원 A 완성 후)
```

---

## 팀원 A와 합의 필요

```
1. dates 테이블의 date_id 타입 (UUID v7 통일 여부)
2. UUID 생성 함수 통일 (gen_random_uuid() vs uuid_generate_v7())
3. 004_fk.sql 작성 시점
```