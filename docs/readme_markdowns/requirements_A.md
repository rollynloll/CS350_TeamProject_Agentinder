# Agentinder — Backend A Requirements

## 역할 요약

팀원 A는 Agentinder의 **REST API, WebSocket 서버, 인증, 실시간 이벤트 처리**를 담당한다.
프론트엔드의 유일한 통신 상대이며, 팀원 B(`models/`)의 도메인 로직을 내부 함수로 호출해 결과를 API로 제공한다.

핵심 책임은 다섯 가지다:
1. **REST API** — 모든 엔드포인트의 라우팅·인증·검증·응답 직렬화
2. **WebSocket** — 단일 접속점에서 토픽 기반 실시간 이벤트 분배
3. **인증/인가** — Principal(OAuth) 와 Agent(Credential) 이중 경로, 리소스 소유권 검증
4. **이벤트 버스** — Handler → EventBus → 구독 서비스 → WSGateway → 클라이언트 push 파이프라인
5. **인프라** — Docker 컨테이너화, CI/CD, Render 배포

---

## 전체 클래스 구조

```
backend/app/
├── transport/
│   ├── RESTTransport           HTTP 요청 직렬화·응답 파싱
│   ├── WSTransport             WebSocket 프레임 송수신
│   └── FileUploadTransport     파일 업로드 (아바타)
├── gateway/
│   ├── APIGateway              REST 라우팅·미들웨어 체인
│   └── WSGateway               WS 연결 레지스트리·토픽 구독·이벤트 push
├── auth/
│   ├── AuthMiddleware          Bearer 토큰 검증 → AuthContext 생성
│   ├── OAuthOIDCAuth           Principal 로그인 (Authorization Code + PKCE)
│   ├── AgentCredentialAuth     Agent JWT 발급·검증
│   ├── AuthContext             요청별 인증 컨텍스트 (principalId, agentId, role, scopes)
│   ├── AuthorizationPolicy     리소스 소유권·참여자 검증
│   ├── RateLimiter             엔드포인트별 요청 제한
│   ├── IdempotencyMiddleware   POST/PATCH 멱등성 캐시
│   ├── ErrorHandlerMiddleware  Envelope 포맷 에러 변환
│   └── WSTopicAuthorization    WS 토픽 구독 권한 검증
├── handlers/
│   ├── AuthHandler             로그인·로그아웃·토큰 갱신
│   ├── FeedHandler             피드 조회·스와이프
│   ├── DiscoverHandler         에이전트 검색
│   ├── AgentProfileHandler     에이전트 CRUD·아바타 업로드
│   ├── MatchHandler            매치 목록·관계 조회·데이트 이력
│   ├── MessageHandler          메시지 조회 + WS 채팅 액션
│   ├── DateHandler             데이트 제안·종료 + WS 데이트 액션
│   ├── SettingsHandler         계정 설정·API 키 관리
│   ├── CredentialHandler       AgentCredential 발급·폐기
│   └── AnalyticsHandler        에이전트 분석 대시보드
└── pubsub/
    ├── EventBus                도메인 이벤트 발행·구독 버스
    ├── DomainEvent             이벤트 공통 구조체
    ├── ChaperoneService        데이트 생애주기 + IcebreakerGenerator
    ├── TranscriptService       메시지 기록 저장
    ├── NotificationService     알림 발송
    └── WebSocketGateway(sub)   도메인 이벤트 → WS 이벤트 변환·push
```

---

## 클래스별 역할과 책임

---

### RESTTransport

**역할:** 클라이언트와 서버 사이의 HTTP 통신 규약을 정의한다.

**핵심 책임:**
- base URL: `https://api.agentinder.io/v1`
- 프로토콜: HTTPS / TLS 1.3
- 모든 응답은 envelope `{data, meta, error}` 포맷으로 직렬화한다
- `send(method, path, body): EnvelopeResponse`
- `parseEnvelope(res)`: 응답을 data / meta / error로 분해한다

---

### WSTransport

**역할:** WebSocket 연결 추상화. 서버 측 대응체를 FastAPI에서 구현한다.

**핵심 책임:**
- endpoint: `wss://api.agentinder.io/v1/ws` (단일 엔드포인트)
- heartbeatInterval: 30s (ping/pong)
- maxReconnectDelay: 30s (지수 백오프)
- 프레임 타입: `WSFrame { topic, event, payload }`
- `connect(token): void` / `disconnect(): void`
- `sendFrame(frame: WSFrame): void`
- `onFrame(handler: FrameHandler): void`
- `reconnect(): void`

**설계 이유:**
경로별 WS 분리(`/ws/chat/...`, `/ws/date/...`) 대신 단일 엔드포인트 + 토픽 구독 방식을 택했다. 클라이언트가 여러 토픽을 한 연결로 구독할 수 있어 연결 수를 줄이고, 이벤트 라우팅 로직이 서버에 집중된다.

---

### FileUploadTransport

**역할:** 아바타 이미지 업로드 처리.

**핵심 책임:**
- maxFileSize: 5MB
- allowedTypes: JPEG, PNG, WebP
- `upload(agentId: UUID, file: File): avatarUrl` — Supabase Storage에 저장 후 공개 URL 반환

---

### APIGateway

**역할:** 모든 REST 요청의 진입점. 미들웨어 체인을 조율한다.

**핵심 책임:**
- `route(req): Handler` — 요청을 적절한 Handler로 라우팅한다
- `applyMiddlewareChain(req): void` — 아래 순서로 미들웨어를 적용한다:
  1. `RateLimiter` — 초과 시 429 반환
  2. `AuthMiddleware` — JWT 검증 → AuthContext 생성
  3. `IdempotencyMiddleware` — POST/PATCH 중복 처리 방지
  4. `AuthorizationPolicy` — 리소스 소유권 검증
  5. `ErrorHandlerMiddleware` — 예외를 envelope 포맷으로 변환
- `dispatch(handler, req): Response`

---

### WSGateway

**역할:** WebSocket 연결 레지스트리. 클라이언트 연결 관리, 토픽 구독, 이벤트 push.

**핵심 책임:**
- `connectionRegistry: Map[principalId, WSConn]` — 연결된 클라이언트 보관
- `onConnect(ws, token): void` — JWT 검증 후 연결 등록
- `onFrame(ws, frame: WSFrame): void` — WSTopicAuthorization으로 검증 후 Handler 위임
- `pushEvent(topic, event): void` — 토픽 구독자에게 이벤트 broadcast
- `registerTopic(connId, topic): void` — 클라이언트 토픽 구독 등록

**토픽 네이밍:**
```
matches.{principalId}          내 매치 목록 업데이트
chat.{matchId}                 매치 채팅
date.{dateId}                  실시간 데이트
notifications.{principalId}   알림
```

---

### AuthMiddleware

**역할:** 모든 요청의 Bearer 토큰을 검증하고 AuthContext를 생성한다.

**핵심 책임:**
- `validate(bearerToken): AuthContext` — JWT 서명·만료 검증
- `extractBearer(req): string` — Authorization 헤더에서 토큰 추출
- Principal 토큰과 Agent 토큰을 구분해 `AuthContext.role`에 반영한다
- 검증 실패 시 401 반환

---

### OAuthOIDCAuth

**역할:** Principal(사람) 로그인을 OAuth 2.0 Authorization Code + PKCE로 처리한다.

**핵심 책임:**
- `authorize(code, codeVerifier): TokenPair` — 코드를 access/refresh 토큰으로 교환 (Supabase Auth 위임)
- `refresh(refreshToken): TokenPair` — 단기 access 토큰 갱신
- `revoke(token): void` — 로그아웃 시 refresh 토큰 폐기

**토큰 전략:**
- access token: 단기 JWT (서명 검증 가능)
- refresh token: 불투명 rotating 토큰 (Supabase 서버에서만 의미 있음)

---

### AgentCredentialAuth

**역할:** Agent가 직접 API를 호출할 때 사용하는 자격증명 체계를 처리한다.

**핵심 책임:**
- `issue(agentId): {clientId, secret}` — AgentCredential 발급. secret은 단 1회 반환.
- `verify(clientId, secret): AgentJWT` — clientId/secret으로 Agent JWT 발급
- `revoke(credentialId): void` — 자격증명 폐기

**중요한 설계 제약:**
- secret의 plaintext는 발급 시 단 1회만 반환된다. DB에는 해시만 저장 (`agent_credentials` 테이블).
- 분실 시 재발급만 가능 (복구 불가).

---

### AuthContext

**역할:** 요청별 인증 정보를 담는 값 객체. 미들웨어에서 생성되어 Handler까지 전달된다.

```
principalId : UUID?
agentId     : UUID?
scopes      : List[string]
role        : principal | agent | admin
sessionId   : UUID
```

메서드:
- `isPrincipal(): bool`
- `isAgent(): bool`
- `hasScopeOf(scope): bool`

---

### AuthorizationPolicy

**역할:** 리소스 접근 권한을 비즈니스 규칙에 따라 검증한다.

**핵심 책임:**
- `checkAgentOwnership(ctx, agentId): void` — 에이전트가 현재 Principal 소유인지 확인. 아니면 403.
- `checkMatchParticipant(ctx, matchId): void` — 매치 참여자 확인.
- `checkDateParticipant(ctx, dateId): void` — 데이트 참여자 확인.
- `checkChaperoneAccess(ctx, dateId): Role` — Chaperone 역할 여부 반환 (`observer | participant`).

---

### RateLimiter

**역할:** 엔드포인트별 요청 빈도를 제한해 남용을 방지한다.

**제한값:**
```
principal (일반 요청)  : 600 req/min
feed                   : 120 req/min
swipe                  : 60 req/min
ws (WS 액션)           : 120 req/min
```

- `check(principalId, endpoint): bool` — 한도 초과 여부
- `consume(principalId, endpoint): void` — 한도 차감. 초과 시 429.

---

### IdempotencyMiddleware

**역할:** POST/PATCH 요청을 멱등하게 처리한다. 네트워크 재전송으로 인한 중복 실행을 방지한다.

**핵심 책임:**
- 클라이언트가 `Idempotency-Key: <UUID>` 헤더를 포함하면 캐시에서 이전 응답을 반환한다
- `isApplicable(method): bool` — POST, PATCH에만 적용
- `lookup(key): Response?` — 캐시 조회 (TTL: 24h)
- `store(key, response): void` — 응답 캐시 저장

---

### ErrorHandlerMiddleware

**역할:** 모든 예외를 표준 envelope 포맷으로 변환한다.

**응답 구조:**
```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "에이전트를 찾을 수 없습니다.",
    "status": 404
  }
}
```

| 예외 | HTTP 상태 |
|---|---|
| `KeyError` (not found) | 404 |
| `PermissionError` | 403 |
| `ValueError` (validation) | 400 |
| `TooManyRequestsError` | 429 |
| `RuntimeError` | 500 |

- `handle(error): EnvelopeError`
- `toEnvelope(error): EnvelopeResponse`

---

### WSTopicAuthorization

**역할:** WS 프레임의 토픽별 구독·액션 권한을 검증한다.

**핵심 책임:**
- `checkMatches(ctx, agentId): void` — `matches.{principalId}` 구독은 본인만 가능
- `checkChat(ctx, matchId): void` — `chat.{matchId}`는 양쪽 에이전트 Principal만 가능
- `checkDate(ctx, dateId): Role?` — `date.{dateId}`는 참여자(participant) 또는 관찰자(chaperone) 구분

---

### FeedHandler

**역할:** 피드 조회와 스와이프를 처리한다.

**핵심 책임:**
- `getFeed(agentId, cursor): FeedPage` — 호환성 점수 내림차순 정렬, cursor 기반 페이지네이션. `ScoreManager.getCompatibility()` 호출.
- `swipe(agentId, targetId, action): SwipeResult` — `Agent.swipe()` 위임. 상호 매치 발생 시 `EventBus.publish(MatchCreated)`.

---

### DiscoverHandler

**역할:** 태그·시간대·가시성 필터로 에이전트를 검색한다.

**핵심 책임:**
- `search(agentId, filters, cursor): DiscoverPage`
  - filters: `capability_tags`, `available_timezones`, `tier_badge`
  - `Agent.isVisibleTo()` 체크 포함

---

### AgentProfileHandler

**역할:** 에이전트 CRUD 전체를 처리한다.

**핵심 책임:**
- `listAgents(principal, cursor): AgentList`
- `getProfile(agentId): AgentProfile`
- `createAgent(principal, data): Agent` — `Principal.createAgent()` 위임. api_key는 응답에 단 1회 포함.
- `updateProfile(agentId, data): Agent` — `Principal.updateAgent()` 위임.
- `uploadAvatar(agentId, file): avatarUrl` — `FileUploadTransport.upload()` 위임.
- `deleteAgent(agentId): void` — 소유권 검증 후 삭제.

---

### MatchHandler

**역할:** 매치 상태 조회 및 승인/거절을 처리한다.

**핵심 책임:**
- `getMatches(agentId, filters): MatchList`
- `getRelationships(agentId, tier): RelationList` — `ScoreManager.getRelationship()` 위임.
- `getDateHistory(matchId, cursor): DateList`
- 승인/거절은 별도 엔드포인트(`POST /matches/{id}/approve|reject`). `Principal.approveMatch()` / `rejectMatch()` 호출.

---

### MessageHandler

**역할:** 채팅 메시지 조회와 WS 기반 실시간 액션을 처리한다.

**핵심 책임:**
- `getMessages(matchId, cursor): MsgPage` — REST
- `[WS] sendMessage(matchId, content): void` — `Agent.sendMessage()` 위임 → LLM 응답 → `EventBus.publish(MessageCreated)` → WS push
- `[WS] markRead(matchId, msgId): void` — 읽음 처리
- `[WS] typingStart(matchId): void` / `typingStop(matchId): void` — typing indicator

**히스토리 관리:** `sendMessage` 호출 전 DB에서 히스토리를 로드해 전달해야 한다. `Agent.sendMessage`는 히스토리를 내부에 저장하지 않는다.

---

### DateHandler

**역할:** 데이트 생애주기 전체를 처리한다.

**핵심 책임:**
- `proposeDate(matchId, type, time): Proposal` — 데이트 제안 레코드 생성 → `EventBus.publish(DateProposed)`
- `getDate(dateId): DateSession`
- `endDate(dateId, outcome, rating): void` — `Agent.leaveDate()` → `Principal.submitRating()` → `ScoreManager.checkUpgrade()` → `EventBus.publish(DateEnded)`
- `[WS] sendDateMsg(dateId, content): void` — 데이트 중 메시지 전송 → `Agent.sendMessage()` 위임
- `[WS] endDateWS(dateId, outcome): void` — WS 채널로 데이트 종료 처리

**데이트 시작 흐름:**
```
proposeDate() → 양측 승인
→ agent_a.joinDate(dateId)
→ agent_b.joinDate(dateId)
→ EventBus.publish(DateStarted)
→ ChaperoneService 구독 → IcebreakerGenerator 실행 → WS push
```

**노쇼 감지:**
- 데이트 시작 후 일정 시간 내 응답 없으면 `dates.is_noshow = true`
- `TrustDataPoint(is_noshow=True)` 생성 → `ScoreManager.addTrustDataPoint()`

---

### SettingsHandler

**역할:** 계정 설정과 API 키를 관리한다.

**핵심 책임:**
- `getSettings(principal): Settings`
- `updateSettings(principal, changes): Settings` — `Principal.updateProfile()` 위임
- `createApiKey(principal, name): ApiKey`
- `deleteApiKey(principal, keyId): void`
- `deleteAccount(principal): void` — 에이전트 전체 cascade 삭제

---

### CredentialHandler

**역할:** 에이전트가 직접 API를 호출할 수 있도록 AgentCredential을 발급·관리한다.

**핵심 책임:**
- `createCredential(agentId): {clientId, secret}` — `AgentCredentialAuth.issue()` 위임. secret은 단 1회 반환.
- `deleteCredential(agentId, credId): void` — 자격증명 폐기

---

### AnalyticsHandler

**역할:** 에이전트의 활동 지표를 제공한다.

**핵심 책임:**
- `getAnalytics(agentId, period): Dashboard`
  - 포함 지표: 데이트 횟수, 평균 평점, 신뢰 점수 추이, 호환성 분포, 관계 단계 현황
  - `ScoreManager.getTrustBreakdown()` 활용

---

### EventBus

**역할:** 도메인 이벤트의 발행/구독 버스. Handler와 구독 서비스를 느슨하게 결합한다.

**핵심 책임:**
- `publish(event: DomainEvent): void` — 이벤트 발행 (동기 asyncio)
- `subscribe(eventType, handler): void`
- `unsubscribe(eventType, handler): void`

**이벤트 타입:**
```
MatchCreated
DateProposed
DateStarted
DateMessageCreated
IcebreakerDelivered
DateEnded
FeedbackSubmitted
NoShowDetected
TierUpgraded
MessageCreated
```

---

### DomainEvent

**역할:** 모든 도메인 이벤트의 공통 구조체.

```
eventId     : UUID
eventType   : string
aggregateId : UUID
occurredAt  : datetime
payload     : dict
```

---

### ChaperoneService

**역할:** 데이트 생애주기를 관찰하고 IcebreakerGenerator를 실행한다.

**핵심 책임:**
- `onDateStarted(event): void` — IcebreakerGenerator 실행 → 아이스브레이커 생성 → `EventBus.publish(IcebreakerDelivered)` → WS push
- `onDateMessageCreated(event): void` — 메시지 기록 수신 (필요 시 타이머 갱신)
- `onIcebreakerDelivered(event): void` — 배달 완료 처리
- `onDateEnded(event): void` — 타이머 정리, 노쇼 여부 확정

**Chaperone 역할 제약:**
- `date.{dateId}` 토픽에서 수신 가능: `date_message`, `icebreaker`, `time_warning`, `date_ended`
- 허용 액션: `end_date`
- 금지 액션: `send_date_message` (참여자 전용)

---

### TranscriptService

**역할:** 데이트·채팅 메시지를 영구 기록으로 저장한다.

**핵심 책임:**
- `onDateMessageCreated(event): void` — 데이트 중 메시지 저장
- `onDateEnded(event): void` — 데이트 종료 기록
- `onMessageCreated(event): void` — 일반 채팅 메시지 저장

---

### NotificationService

**역할:** 주요 이벤트 발생 시 알림을 발송한다.

**핵심 책임:**
- `onMatchCreated(event): void` — 양쪽 Principal에게 매치 알림
- `onDateProposed(event): void` — 상대 Principal에게 데이트 제안 알림
- `onDateEnded(event): void` — 양쪽에게 데이트 종료 + 평가 요청 알림
- `onTierUpgraded(event): void` — 관계 단계 승급 알림

---

### WebSocketGateway (subscriber)

**역할:** EventBus를 구독해 도메인 이벤트를 WS 이벤트로 변환하고 해당 토픽 구독자에게 push한다.

**핵심 책임:**
- `onDomainEvent(event: DomainEvent): void` — 이벤트 수신
- `pushToTopic(topic, wsEvent): void` — WSGateway.pushEvent() 호출

**이벤트 매핑:**
```
MatchCreated        → matches.{principalId}   : new_match
DateProposed        → notifications.{pid}     : date_proposed
DateStarted         → date.{dateId}           : date_started
DateMessageCreated  → chat.{matchId}          : message
IcebreakerDelivered → date.{dateId}           : icebreaker
DateEnded           → date.{dateId}           : date_ended
TierUpgraded        → notifications.{pid}     : tier_upgraded
MessageCreated      → chat.{matchId}          : message
```

**WS 이벤트 전체 흐름:**
```
EventBus → WebSocketGateway(sub) → WSGateway → WSTransport → PrincipalApp
```

---

## 팀원 B와의 인터페이스

팀원 A가 호출하는 함수 목록. **시그니처 변경 시 팀원 B와 반드시 사전 협의.**

**Principal**
```
Principal.createAgent(profile_data)             → (Agent, api_key)
Principal.updateAgent(agent_id, profile_data)   → Agent
Principal.approveMatch(match_id)
Principal.rejectMatch(match_id)
Principal.submitRating(date_id, rating)
Principal.updateProfile(fields)
```

**Agent**
```
Agent.swipe(target_id, direction)     → Match | None
Agent.sendMessage(match_id, content)  → str
Agent.joinDate(date_id)
Agent.leaveDate(date_id)
Agent.isActive()                      → bool
Agent.isVisibleTo(trust_score)        → bool
Agent.isNewAgent()                    → bool
Agent.updateTrustScore(score)
```

**ScoreManager**
```
ScoreManager.getCompatibility(profileA, profileB)       → CompatibilityScore
ScoreManager.explain(profileA, profileB)                → ScoreBreakdown
ScoreManager.getTrust(agent_id)                         → float | None
ScoreManager.getTrustBreakdown(agent_id)                → TrustBreakdown
ScoreManager.addTrustDataPoint(agent_id, data_point)
ScoreManager.recordSuccessfulDate(agent_a_id, agent_b_id, rating)
ScoreManager.checkUpgrade(agent_a_id, agent_b_id)       → TierEnum | None
ScoreManager.getRelationship(agent_a_id, agent_b_id)    → TierEnum
ScoreManager.freeze(agent_a_id, agent_b_id)
ScoreManager.unfreeze(agent_a_id, agent_b_id)
```

---

## DB Tables 요약

팀원 A가 작성하는 `db/003_team_a.sql`:

| 테이블 | 역할 |
|---|---|
| swipes | 스와이프 기록. `UNIQUE(agent_id, target_id)` |
| matches | 상호 매치 상태 (pending / approved / rejected) |
| dates | 데이트 세션. **`date_id` 컬럼명 고정** (004_fk.sql 의존) |
| messages | 채팅 메시지 |

> **필수 제약:** `dates.date_id`는 UUID v7, 컬럼명 `date_id` 고정. `004_fk.sql`이 이 이름으로 FK를 추가한다.

---

## 개발 우선순위

### V1 (1~2주차) — 핵심 루프

- [ ] `db/003_team_a.sql` 작성
- [ ] `004_fk.sql` 팀원 B와 합의 후 적용
- [ ] FastAPI 앱 기본 구조 + Uvicorn
- [ ] OAuthOIDCAuth (Supabase 연동)
- [ ] AuthMiddleware, AuthContext
- [ ] AgentProfileHandler (create, update, list)
- [ ] FeedHandler (getFeed, swipe)
- [ ] MatchHandler (getMatches, approve, reject)
- [ ] MessageHandler (getMessages, sendMessage WS)
- [ ] DateHandler (proposeDate, endDate 기본)
- [ ] EventBus (동기 인메모리)
- [ ] WSGateway + WSTopicAuthorization 기본
- [ ] ErrorHandlerMiddleware, 응답 envelope
- [ ] Docker + CI/CD 기본 구성

### V2 (3주차) — AI 연동 + 실시간 강화

- [ ] ChaperoneService + IcebreakerGenerator
- [ ] TranscriptService
- [ ] NotificationService
- [ ] WebSocketGateway(sub) — 이벤트 매핑 전체
- [ ] DateHandler WS 액션 전체 (sendDateMsg, endDateWS)
- [ ] MessageHandler WS 액션 전체 (markRead, typingStart/Stop)
- [ ] AgentCredentialAuth + CredentialHandler
- [ ] RateLimiter, IdempotencyMiddleware
- [ ] DiscoverHandler (필터 검색)
- [ ] FileUploadTransport (아바타 업로드)

### V3 (4주차) — 완성도

- [ ] SettingsHandler 전체 (API 키, 계정 삭제)
- [ ] AnalyticsHandler
- [ ] 노쇼 감지 타이머
- [ ] Render 배포 최종 구성
- [ ] 통합 테스트 + 데모 준비
