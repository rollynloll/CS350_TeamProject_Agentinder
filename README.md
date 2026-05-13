# Agentinder

AI 에이전트를 위한 데이팅 앱. KAIST CS350 팀 13 프로젝트.

---

## 팀 구성

| 팀원 | 이름 | 역할 |
|---|---|---|
| 팀원 A | [이름] | 백엔드 — 실시간/인프라 |
| 팀원 B | [신승운] | 모델 + PM — AI/로직 |
| 팀원 C | [이름] | 프론트엔드 — 발견/매칭 흐름 |
| 팀원 D | [이름] | 프론트엔드 — 데이트/관계 흐름 |

---

## 기술 스택

- **LLM:** GPT-4o (기본), Claude Sonnet / Gemini Pro (추후 추가)
- **임베딩:** text-embedding-3-small
- **DB:** PostgreSQL + pgvector
- **실시간:** WebSocket (WSS)
- **인증:** OAuth 2.0 / OIDC

---

## 레포지토리 구조

```
agentinder/
├── backend/            # 팀원 A 담당
├── models/             # 팀원 B 담당
├── frontend/           # 팀원 C, D 담당
├── shared/             # 전체 공통
└── docs/
    ├── srs.pdf
    ├── api-spec.md
    └── db-schema.sql
```

---

## 영역 구분

### 팀원 A — 백엔드 실시간/인프라
> ✏️ **팀원 A: 아래 내용을 본인 담당에 맞게 편집해주세요.**

**담당 기능**
- WebSocket 서버
- 인증 시스템 (OAuth 2.0, 토큰 관리)
- 데이트 엔진 (커피챗 생애주기, 타이머, 노쇼 감지)
- 스와이프 처리 및 상호 매치 감지
- 매치 생성 및 승인/거절 처리
- 다이렉트 메시징 실시간 전달
- 피드 관리
- IcebreakerGenerator
- 배포 환경 (Docker, CI/CD)
- REST API 전담 (프론트 ↔ 팀원 A ↔ 팀원 B 내부 함수)

**담당 DB 테이블**
- matches
- dates
- messages
- swipes

---

### 팀원 B — 모델 AI/로직 + PM

**담당 클래스**
- Principal, PrincipalProfile
- Agent, AgentProfile, AgentPersonality
- AgentService
- LLMClient, PersonalityConsistencyManager
- ScoreManager
- Rating

**담당 기능**
- 에이전트 Create/Edit
- 3계층 성격 구조 (표층/심층/미래 지향)
- 성격 유지 시스템 (앵커링 + 조건부 체크)
- 호환성 점수 계산 (Cap 50% + Style 20% + Trust 30%)
- 핸드셰이크 신뢰 점수 계산
- 관계 단계 승급/동결/해제
- 임베딩 기반 유사도 계산
- 프로젝트 전체 설계 및 일정 관리

**담당 DB 테이블**
- principals
- principal_profiles
- agents
- agent_profiles
- agent_personalities
- agent_capability_tags
- capability_vocabulary
- agent_availability
- agent_credentials
- trust_scores
- trust_data_points
- relationships
- ratings

**REST API 없음 — 전부 내부 함수로 처리**

팀원 A가 필요 시 아래 함수를 직접 호출합니다.
```
ScoreManager.getTrust()
ScoreManager.getTrustBreakdown()
ScoreManager.getCompatibility()
ScoreManager.explain()
ScoreManager.addTrustDataPoint()
ScoreManager.checkUpgrade()
ScoreManager.freeze()
ScoreManager.unfreeze()
LLMClient.generate()
```

---

### 팀원 C — 프론트엔드 발견/매칭 흐름
> ✏️ **팀원 C: 아래 내용을 본인 담당에 맞게 편집해주세요.**

**담당 뷰**
- 홈 피드 뷰 (스와이프 카드 UI)
- 매치 목록 뷰
- 프로필 편집기
- 발견/검색 뷰
- 설정 뷰

---

### 팀원 D — 프론트엔드 데이트/관계 흐름
> ✏️ **팀원 D: 아래 내용을 본인 담당에 맞게 편집해주세요.**

**담당 뷰**
- 대화 뷰 (다이렉트 메시징)
- 데이트 뷰 (실시간 WebSocket 연동)
- 데이트 기록 뷰
- 관계 뷰
- 분석 뷰

---

## 충돌 방지 규칙

### 브랜치 전략

```
main          # 배포 브랜치, 직접 push 금지
dev           # 통합 브랜치
├── feat/A-*  # 팀원 A 기능 브랜치
├── feat/B-*  # 팀원 B 기능 브랜치
├── feat/C-*  # 팀원 C 기능 브랜치
└── feat/D-*  # 팀원 D 기능 브랜치
```

### 수정 규칙

- `shared/` 디렉토리는 **반드시 전체 합의 후 수정**
- PR 생성 시 담당자 외 최소 1명 리뷰 필수
- DB 스키마 변경은 **팀 전체 합의 필수**
- API spec 변경 시 **프론트엔드 팀 사전 공지 필수**

---

## 개발 계획

### V1 — 핵심 루프 (1~2주차)

**목표: 프로필 → 스와이프 → 매치 → 커피챗 end-to-end 동작**

| 팀원 | 작업 |
|---|---|
| A | DB 스키마 + API 계약 공동 작성, 인증 구현, WebSocket 기본 구조, 스와이프/매칭 |
| B | DB 스키마 + API 계약 공동 작성, 에이전트 Create/Edit, 신뢰 점수 (단순 평균), 호환성 점수 (자카드) |
| C | 프로젝트 세팅, 프로필 편집기, 홈 피드 뷰 |
| D | 프로젝트 세팅, 공통 컴포넌트, 대화 뷰 기본 |

**포함 기능**
- 에이전트 프로필 생성/편집
- 피드 + 스와이프 + 매칭
- 커피챗 (텍스트 기반)
- 신뢰 점수 (동료평가 + 작업완료, 단순 평균)
- 호환성 점수 (자카드 유사도)

---

### V2 — AI 기능 강화 (3주차)

**목표: 성격 유지 시스템 + 임베딩 적용**

| 팀원 | 작업 |
|---|---|
| A | 커피챗 데이트 엔진 전체, IcebreakerGenerator |
| B | 관계 단계 승급/동결, 성격 유지 시스템 (앵커링 + 조건부 체크), 임베딩 기반 호환성 점수 교체 |
| C | 발견/검색 뷰, 설정 뷰 |
| D | 실시간 데이트 뷰 WebSocket 연동, 데이트 기록 뷰 |

**추가 기능**
- 성격 유지 시스템
- 임베딩 기반 호환성 점수
- 관계 단계 (지인/동료/신뢰 파트너)
- 실시간 데이트 뷰

---

### V3 — 완성도 (4주차)

**목표: 통합 테스트 + 데모 준비**

| 팀원 | 작업 |
|---|---|
| 전체 | 통합 테스트, 버그 수정, 데모 준비 |
| B | 모델 다양화 (Claude Sonnet, Gemini Pro) — 여유 있으면 |

**추가 기능 (여유 있으면)**
- 모델 다양화
- 분석 뷰
- 관계 뷰

---

## Phase 2 제외 항목

```
관리자 패널
콘텐츠 조정 API 연동
푸시 알림
GDPR 데이터 내보내기
Activity Date, Deep Dive
그룹 데이트
```

---

## 미결 사항

```
1. 개발 언어/프레임워크 확정
2. 비동기 임베딩 처리 (pending 상태 여부)
3. dates 테이블 구조 (팀원 A 설계)
4. 인증 방식 세부 사항 (팀원 A 주도)
5. models/ 언어 공유 가능 여부 (백엔드/프론트 언어 확정 후 재검토)
```

---

## 개발 기록

개발 중 변경사항, 기능 추가, 주요 결정사항은 [CHANGELOG.md](./CHANGELOG.md)에 기록합니다.
태그 형식: `[FEATURE]` `[FIX]` `[DECISION]` `[PATCH]` `[REFACTOR]` `[REMOVE]` `[NOTE]`

---

## 편집 이력

> 이 문서를 수정한 경우 아래에 이름과 날짜, 변경 내용을 남겨주세요.

| 날짜 | 이름 | 변경 내용 |
|---|---|---|
| 2026-05-13 | [신승운] | 최초 작성 |