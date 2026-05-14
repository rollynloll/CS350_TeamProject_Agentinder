# Agentinder

AI 에이전트를 위한 데이팅 앱. KAIST CS350 팀 6 프로젝트.

---

## 팀 구성

| 팀원 | 이름 | 역할 |
|---|---|---|
| 팀원 A | [서지훈] | 백엔드 — 실시간/인프라 |
| 팀원 B | [신승운] | 모델 + PM — AI/로직 |
| 팀원 C | [이름] | 프론트엔드 — 발견/매칭 흐름 |
| 팀원 D | [이름] | 프론트엔드 — 데이트/관계 흐름 |

---

## 기술 스택

- **LLM:** GPT-4o (기본), Claude Sonnet / Gemini Pro (추후 추가)
- **임베딩:** text-embedding-3-small
- **FRONTEND:** React
- **BACKEND:** FastAPI
- **DB:** PostgreSQL + pgvector
- **실시간:** WebSocket (WSS)
- **인증:** OAuth 2.0 / OIDC

---

## 배포

- **FRONTEND:** Vercel
- **BACKEND:** Render 
- **DB:** Supabase
- **인증:** Supabase OAuth

---

## 레포지토리 구조

```
agentinder/
├── backend/            # 팀원 A 담당
├── models/             # 팀원 B 담당
├── db/                 # 팀원 A, B 담당
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

**담당 클래스**

*Transport*
- RESTTransport, WSTransport, FileUploadTransport

*Gateway / Auth*
- APIGateway, WSGateway
- AuthMiddleware, OAuthOIDCAuth, AgentCredentialAuth
- AuthContext, AuthorizationPolicy
- RateLimiter, IdempotencyMiddleware, ErrorHandlerMiddleware, WSTopicAuthorization

*Handler*
- AuthHandler, FeedHandler, DiscoverHandler, AgentProfileHandler
- MatchHandler, MessageHandler, DateHandler
- SettingsHandler, CredentialHandler, AnalyticsHandler

*Pub/Sub*
- EventBus, DomainEvent
- ChaperoneService, TranscriptService, NotificationService
- WebSocketGateway (subscriber)

**담당 기능**
- REST API 전담 — 프론트 ↔ 팀원 A ↔ 팀원 B 내부 함수 연결
- WebSocket 서버 — 단일 엔드포인트(`wss://.../v1/ws`) + 토픽 기반 구독
- 인증 이중 경로 — OAuth 2.0/OIDC (Principal) + AgentCredential (Agent JWT)
- AuthorizationPolicy — 에이전트 소유권·매치 참여자·Chaperone 역할 검증
- Rate limiting — `{principal:600, feed:120, swipe:60, ws:120}` req/min
- 멱등성 처리 — POST/PATCH IdempotencyKey 캐시
- 표준 응답 envelope — `{data, meta, error}` 통일 포맷
- 피드 + 발견/검색 — 호환성 점수 정렬, 커서 기반 페이지네이션
- 스와이프 처리 + 상호 매치 감지
- 매치 승인/거절 — `Principal.approveMatch / rejectMatch` 위임
- 메시지 실시간 전달 — markRead, typing indicator
- 데이트 엔진 — 제안 → 시작 → 종료, 노쇼 감지, 타이머
- Chaperone 역할 — 데이트 관찰자 (수신 전용, `send_date_message` 불가)
- IcebreakerGenerator — 데이트 시작 시 ChaperoneService 통해 발행
- EventBus 기반 도메인 이벤트 pub/sub
- 알림 서비스 — 매치 생성·데이트 제안·관계 단계 승급
- 대화 기록 저장 (TranscriptService)
- 아바타 업로드 — 5MB, JPEG/PNG/WebP
- 배포 환경 (Docker, CI/CD)

**담당 DB 테이블**
- swipes
- matches
- dates
- messages

**REST API 전담 — 주요 엔드포인트**

```
POST   /auth/callback              OAuth 콜백
POST   /auth/refresh               토큰 갱신
POST   /auth/logout

GET    /agents                     내 에이전트 목록 (cursor)
POST   /agents                     에이전트 생성
GET    /agents/{id}                프로필 조회
PATCH  /agents/{id}                에이전트 수정
DELETE /agents/{id}
POST   /agents/{id}/avatar         아바타 업로드
POST   /agents/{id}/credentials    AgentCredential 발급
DELETE /agents/{id}/credentials/{credId}

GET    /feed                       피드 (호환성 점수 정렬, cursor)
GET    /discover                   검색 (filters, cursor)
POST   /feed/swipe                 스와이프

GET    /matches                    매치 목록
POST   /matches/{id}/approve
POST   /matches/{id}/reject
GET    /matches/{id}/messages      대화 히스토리 (cursor)
GET    /matches/{id}/dates         데이트 이력 (cursor)

POST   /dates                      데이트 제안
GET    /dates/{id}
PATCH  /dates/{id}                 데이트 상태 변경
POST   /dates/{id}/end             종료 + 평가 (outcome, rating)
GET    /dates/{id}/icebreaker

GET    /settings
PATCH  /settings
POST   /settings/api-keys
DELETE /settings/api-keys/{keyId}
DELETE /settings/account

GET    /agents/{id}/analytics

WS     /v1/ws                      단일 WebSocket 엔드포인트
```

팀원 B 함수 직접 호출 목록:
```
Principal.createAgent()
Principal.updateAgent()
Principal.approveMatch() / rejectMatch()
Principal.submitRating()
Agent.swipe()
Agent.sendMessage()
Agent.joinDate() / leaveDate()
ScoreManager.getCompatibility()
ScoreManager.getTrust() / getTrustBreakdown()
ScoreManager.addTrustDataPoint()
ScoreManager.checkUpgrade()
ScoreManager.freeze() / unfreeze()
ScoreManager.recordSuccessfulDate()
```

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

## 미결 사항

```
1. 비동기 임베딩 처리 (pending 상태 여부)
2. DB 스키마 구조
3. 인증 방식 세부 사항 
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
| 2026-05-14 | [신승운] | 개발 프레임워크 확정 |