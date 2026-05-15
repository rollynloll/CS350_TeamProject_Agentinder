# Agentinder

AI 에이전트를 위한 데이팅 앱. KAIST CS350 팀 6 프로젝트.

---

## 팀 구성

| 팀원 | 이름 | 역할 |
|---|---|---|
| 팀원 A | [서지훈] | 백엔드 — 실시간/인프라 |
| 팀원 B | [신승운] | 모델 + PM — AI/로직 |
| 팀원 C | [이상진] | 앱 UI/UX 디자인 |
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

### 팀원 C — 앱 UI/UX 디자인

**담당**
- 각 화면 레이아웃 및 GUI 설계
- UX 인터랙션 구조 설계

---

### 팀원 D — 프론트엔드 데이트/관계 흐름

**담당 뷰 / 컴포넌트**

*View (페이지 단위)*
- ConversationView — 1:1 메시징 (Screen ⑩ / SRS Conversation View)
- DateView — 실시간 Date 세션 (Screen ⑨ / SRS Date View)
- DateHistoryDetail — 특정 매치의 데이트 이력 + 평가 (Screen ⑧ / SRS Date History)
- RelationshipsView — 관계 단계별 소셜 네트워크 시각화 (SRS Relationships View, 와이어프레임 신규 설계)
- AnalyticsView — 에이전트 통계 대시보드 (Screen ⑥ / SRS Analytics View)

*공통 컴포넌트*
- WebSocketProvider — 앱 전역 단일 연결, topic 기반 subscribe/unsubscribe
- ChatBubble, MessageList, TypingIndicator, ReadReceipt
- IcebreakerCard — Date 시작 시 3개 프롬프트 표시
- DateTimer — 경과시간 / 남은시간 카운트다운
- ScheduleDateModal — 데이트 타입(Coffee Chat / Activity / Deep Dive) 선택 + 시간 협의
- PostDateRatingForm — 1~5점 + compatibility 슬라이더 + 코멘트 280자 (REQ-0307)
- RelationshipTierBadge — Stranger / Acquaintance / Colleague / Trusted Partner

**담당 기능**
- WebSocket 클라이언트 — 단일 연결, multiplexing (`chat.{matchId}`, `date.{dateId}`)
- 자동 재연결 — exponential backoff (1s → 2s → 4s → 8s → 30s, 30초 ping/pong heartbeat)
- 1:1 메시지 — 실시간 송수신, 읽음 처리 (markRead), 타이핑 인디케이터
- Optimistic update — 메시지 전송 시 즉시 UI 반영, 서버 ACK 시 확정 / 실패 시 rollback
- Schedule Date 플로우 — 채팅에서 데이트 제안 → 타입 선택 → 시간 협의 → 확정 (UC-0301)
- Coffee Chat 진행 화면 — icebreaker 프롬프트 표시, 메시지 스트림, 경과시간, "End Date" 버튼 (UC-0302)
- 노쇼 / 재연결 처리 — 5분 미입장 안내, 3분 재연결 grace period UI
- Chaperone 모드 — Principal 시점 read-only 관전, `send_date_message` 비활성 (UC-0602, REQ-0309)
- Post-Date Rating — 종료 72시간 이내 평가 폼, 이슈 체크박스(hallucination / latency / unresponsive 등) (UC-0502)
- Date History 상세 — outcome, transcript 스크롤, 매치 단위 데이트 카드 리스트
- Relationships View — tier별 그룹화, 관계 health 인디케이터, 상호 endorsement 표시 (REQ-0405, REQ-0407)
- Unmatch 플로우 — 확인 모달, 진행 중 Date 존재 시 차단 (UC-0403)
- Analytics 차트 — trust score 추이(시계열), date 성공률, 호환성 영역 top 5, tier 분포, 주간 활동 요약 (REQ-0605)
- Envelope 응답 파싱 — `{data, meta, error}` 공통 처리, cursor 기반 페이지네이션 무한 스크롤
- Idempotency-Key 헤더 — POST/PATCH 요청 시 UUID 생성하여 재시도 안전성 확보

**호출 API — 팀원 A 제공**

*REST*
```
GET    /matches/{matchId}/messages       대화 히스토리 (cursor)
POST   /matches/{matchId}/dates          Date 제안
GET    /matches/{matchId}/dates          매치의 Date 이력 (cursor)
GET    /dates/{dateId}                   Date 세션 조회
PATCH  /dates/{dateId}                   상태 변경
POST   /dates/{dateId}/end               종료 + 평가 제출
GET    /dates/{dateId}/icebreaker        icebreaker 조회
GET    /agents/{agentId}/relationships   관계 목록 (tier별)
GET    /agents/{agentId}/analytics       통계 데이터
```

*WebSocket (`wss://api.agentinder.io/v1/ws`)*
```
chat.{matchId}    수신: message, typing, read
                  송신: send_message, mark_read, typing_start, typing_stop

date.{dateId}     수신: date_message, icebreaker_prompt, time_warning, date_ended
                  송신: send_date_message, end_date
```

**대응 SRS 요구사항**
- Dates: UC-0301 ~ UC-0304, REQ-0301 ~ REQ-0310
- Relationships & Messaging: UC-0401 ~ UC-0403, REQ-0401 ~ REQ-0407
- Handshake (rating 제출): UC-0502
- Principal Dashboard: UC-0602 (Chaperone), REQ-0605 (Analytics)

**기술 스택**

확정
- React (README 공통 스택)

미정 — 1주차 합의 필요
- 라우팅: React Router vs Next.js App Router
- 상태관리 / 서버 캐시: Zustand + TanStack Query vs Redux Toolkit
- 스타일링: Tailwind CSS vs CSS-in-JS (emotion / styled-components)
- WebSocket 클라이언트: 네이티브 WebSocket vs `socket.io-client`
- 차트: Recharts vs Chart.js
- 폼: React Hook Form + Zod

**팀 의존성**
- ← 팀원 C: 각 뷰의 UI 디자인 / 인터랙션 명세 (Figma or 와이어프레임)
- ← 팀원 A: REST 엔드포인트 + WebSocket 토픽 (envelope 포맷, 토픽명 변경 시 사전 공지)
- ← 팀원 B: 응답 페이로드의 도메인 타입 (Agent, Match, Date, Relationship, RatingForm)
- → 팀원 A: 메시지/Date 송신 액션, 클라이언트 사이드 검증 룰 피드백

**개발 산출물 위치**
```
frontend/
├── src/
│   ├── views/           # ConversationView, DateView, ...
│   ├── components/      # ChatBubble, IcebreakerCard, ...
│   ├── hooks/           # useWebSocket, useDateSession, ...
│   ├── api/             # REST 클라이언트, envelope 파싱
│   └── ws/              # WebSocketProvider, topic registry
└── public/
```

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
| C | 메인 피드 뷰 UI 디자인, 스와이프 인터랙션 설계, 매칭 뷰 및 채팅 뷰 UI 디자인 |
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
| C | 기타 부가적인 뷰 UI 설계 및 UX 사용성 검증 |
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
| 2026-05-15 | [팀원 D] | 팀원 D 담당 영역 작성 (뷰/컴포넌트, 기능, 호출 API, SRS 매핑, 기술 스택 후보) |
