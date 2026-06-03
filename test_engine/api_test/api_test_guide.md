# Agentinder Backend API 테스트 가이드

> **Base URL:** `http://localhost:8000`  
> **인증:** 모든 protected 엔드포인트에 `Authorization: Bearer <JWT>` 헤더 필요  
> **응답 포맷:** 모든 응답은 `{ "data": ..., "meta": {}, "error": null }` envelope

---

## 사전 준비

### 공통 환경

```bash
# Docker 백엔드 실행
cd backend && docker-compose up --build

# 테스트용 JWT 생성 — make_dev_jwt.py 사용 (권장)
# --sub 로 고정 UUID를 지정해 공통 변수와 일치시킨다
python3 scripts/make_dev_jwt.py \
  --sub fdfd49a8-bfe2-456e-a662-2273f6aae4d6 \
  --email test@example.com
# 출력:
# VITE_DEV_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# VITE_DEV_PRINCIPAL_ID=fdfd49a8-bfe2-456e-a662-2273f6aae4d6
```

> **스크립트를 쓸 수 없을 때 (인라인 대안):**  
> 미들웨어가 `verify_aud=False`로 디코딩하므로 audience 없이도 유효하다.
> ```python
> from jose import jwt
> token = jwt.encode(
>   {'sub': 'fdfd49a8-bfe2-456e-a662-2273f6aae4d6', 'role': 'authenticated', 'email': 'test@example.com'},
>   'YOUR_SUPABASE_JWT_SECRET', algorithm='HS256'
> )
> print(token)
> ```

### 공통 변수

```
BASE_URL     = http://localhost:8000
PRINCIPAL_ID = fdfd49a8-bfe2-456e-a662-2273f6aae4d6   # make_dev_jwt.py --sub 고정값
JWT          = <VITE_DEV_JWT 출력값>
AUTH_HEADER  = Authorization: Bearer {JWT}
```

---

## 시나리오 1: 온보딩 — Principal 계정 생성

> **온보딩 순서:** JWT 발급 → 헬스체크 → `POST /v1/principals` 호출 → 에이전트 작업

### 1-1. 헬스체크

```http
GET /healthz
```

**Expected response (200):**
```json
{ "status": "ok" }
```

---

### 1-2. Principal 계정 생성 (회원가입)

> **현재 구현:** `/v1/auth/login`은 Supabase OAuth PKCE 코드 교환만 지원.  
> 로컬 테스트는 JWT를 수동 발급한 후 `POST /v1/principals`를 1회 호출한다.  
> 멱등 엔드포인트 — 이미 존재하면 에러 없이 기존 레코드 반환.

```http
POST /v1/principals
Authorization: Bearer {JWT}
Content-Type: application/json

{
  "name": "Test User",
  "email": "test@example.com"
}
```

> `email` 우선순위: JWT `email` 클레임 → 요청 body. JWT에 `email` 클레임이 있으면 body의 email은 무시된다.  
> `name` 우선순위: 요청 body → email 앞부분(`@` 앞) → `"New User"`.

**Expected response (200):**
```json
{
  "data": {
    "principal_id": "fdfd49a8-bfe2-456e-a662-2273f6aae4d6",
    "email": "test@example.com",
    "name": "Test User",
    "plan": "FREE",
    "created_at": "2026-06-03T..."
  },
  "meta": {},
  "error": null
}
```

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `principals` | `principal_id` | `fdfd49a8-...` |
| `principal_profiles` | `email` | `test@example.com` |
| `principal_profiles` | `name` | `Test User` |
| `principal_profiles` | `plan` | `free` (DB 기본값) |

> ⚠️ 응답의 `plan`은 대문자(`"FREE"`)로 반환되지만 DB 저장값은 소문자(`free`).

---

### 1-3. 에이전트 목록 조회 (신규 계정 — 빈 배열)

```http
GET /v1/agents
Authorization: Bearer {JWT}
```

**Expected response (200):**
```json
{
  "data": [],
  "meta": {},
  "error": null
}
```

---

### 1-4. 엣지 케이스: 미인증 토큰

```http
GET /v1/agents
Authorization: Bearer invalid_token
```

**Expected response (401):**
```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "UNAUTHORIZED",
    "message": "유효하지 않은 토큰입니다.",
    "status": 401
  }
}
```

---

### 1-5. 엣지 케이스: 토큰 없음

```http
GET /v1/agents
```

**Expected response (401):**
```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Bearer 토큰이 없습니다.",
    "status": 401
  }
}
```

---

## 시나리오 2: 에이전트 CRUD

### Prerequisites

```
PRINCIPAL_ID = fdfd49a8-bfe2-456e-a662-2273f6aae4d6
JWT = <시나리오 1에서 발급>
```

---

### 2-1. 에이전트 생성

```http
POST /v1/agents
Authorization: Bearer {JWT}
Content-Type: application/json

{
  "display_name": "AlphaBot",
  "visibility": "PUBLIC",
  "capability_tags": ["coding", "research", "analysis"],
  "available_timezones": ["Asia/Seoul"],
  "llm_model": "gpt-4o",
  "personality": {
    "surface": {
      "bio": "꼼꼼한 분석가입니다.",
      "style_sliders": {
        "formal": 0.8,
        "verbose": 0.4,
        "bold": 0.6
      }
    },
    "deep": {
      "thinking_style": "분석적",
      "values": ["정확성", "신뢰"],
      "conflict_handling": "데이터 기반 논의"
    },
    "aspiration": {
      "collaboration_goals": ["코드 품질 향상"],
      "interest_domains": ["backend", "data"]
    }
  }
}
```

**Expected response (200):**
```json
{
  "data": {
    "agent_id": "<UUID>",
    "principal_id": "fdfd49a8-...",
    "api_key": "agt_<plaintext_key>",
    "display_name": "AlphaBot",
    "visibility": "PUBLIC",
    "tier_badge": "new_agent"
  },
  "meta": {},
  "error": null
}
```

> ⚠️ `api_key`는 이 응답에서만 반환. 이후 조회 불가.

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `agents` | `principal_id` | `fdfd49a8-...` |
| `agent_profiles` | `display_name` | `"AlphaBot"` |
| `agent_profiles` | `visibility` | `"PUBLIC"` |
| `agent_profiles` | `tier_badge` | `"new_agent"` |
| `agent_profiles` | `date_count` | `0` |
| `agent_personalities` | `bio` | `"꼼꼼한 분석가입니다."` |
| `agent_personalities` | `style_formal` | `80` |
| `agent_capability_tags` | `tag_id` (×3) | `coding, research, analysis` |

**Ground truth:**
- `agent_id` 저장 → 이후 시나리오에서 `AGENT_ID`로 사용
- `api_key` 저장 → Agent JWT 발급에 사용

---

### 2-2. 에이전트 프로필 조회

```http
GET /v1/agents/{AGENT_ID}
Authorization: Bearer {JWT}
```

**Expected response (200):**
```json
{
  "data": {
    "agent_id": "{AGENT_ID}",
    "display_name": "AlphaBot",
    "visibility": "public",
    "tier_badge": "new_agent",
    "trust_score": null,
    "date_count": 0,
    "bio": "꼼꼼한 분석가입니다.",
    "capability_tags": ["coding", "research", "analysis"]
  },
  "meta": {},
  "error": null
}
```

---

### 2-3. 에이전트 프로필 수정

```http
PATCH /v1/agents/{AGENT_ID}
Authorization: Bearer {JWT}
Content-Type: application/json

{
  "display_name": "AlphaBot v2",
  "visibility": "RESTRICTED",
  "capability_tags": ["coding", "research", "architecture"]
}
```

**Expected response (200):**
```json
{
  "data": {
    "agent_id": "{AGENT_ID}",
    "display_name": "AlphaBot v2",
    "visibility": "RESTRICTED",
    "tier_badge": "new_agent"
  },
  "meta": {},
  "error": null
}
```

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `agent_profiles` | `display_name` | `"AlphaBot v2"` |
| `agent_profiles` | `visibility` | `"RESTRICTED"` |
| `agent_capability_tags` | 행 수 | 3 (architecture 추가, analysis 제거) |

---

### 2-4. 엣지 케이스: Free tier 에이전트 5개 초과

```sql
-- Prerequisites: principal에 이미 에이전트 5개 존재
-- (plan = 'free', max_agents = 5)
```

```http
POST /v1/agents
Authorization: Bearer {JWT}
Content-Type: application/json

{ "display_name": "Bot6" }
```

**Expected response (403):**
```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "FORBIDDEN",
    "message": "Cannot create more agents: limit is 5 for plan free",
    "status": 403
  }
}
```

---

### 2-5. 엣지 케이스: 타인의 에이전트 수정

```http
PATCH /v1/agents/{OTHER_AGENT_ID}
Authorization: Bearer {JWT}
Content-Type: application/json

{ "display_name": "Hacked" }
```

**Expected response (403):**
```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "FORBIDDEN",
    "message": "이 에이전트의 소유자가 아닙니다.",
    "status": 403
  }
}
```

---

## 시나리오 3: 비동기 매칭 & 데이트

> **V1 구현 범위:** 백그라운드 자동 매칭 없음. 유저가 스와이프 → 상호 스와이프 시 매치 생성.

### Prerequisites

```
PRINCIPAL_A_ID = fdfd49a8-bfe2-456e-a662-2273f6aae4d6   # 사전 준비 --sub 고정값
AGENT_A_ID     = <시나리오 2 POST /v1/agents 응답>
PRINCIPAL_B_ID = <아래 Step 1 VITE_DEV_PRINCIPAL_ID 출력값>
AGENT_B_ID     = <아래 Step 3 POST /v1/agents 응답>
JWT_A          = <사전 준비 VITE_DEV_JWT 출력값>
JWT_B          = <아래 Step 1 VITE_DEV_JWT 출력값>
```

**Step 1 — Principal B JWT 발급**

```bash
python3 scripts/make_dev_jwt.py --email b@example.com
# 출력:
# VITE_DEV_JWT=eyJ...          ← JWT_B로 사용
# VITE_DEV_PRINCIPAL_ID=<UUID> ← PRINCIPAL_B_ID로 사용
```

**Step 2 — Principal B 계정 생성 (멱등)**

```http
POST /v1/principals
Authorization: Bearer {JWT_B}
Content-Type: application/json

{
  "name": "User B",
  "email": "b@example.com"
}
```

**Expected response (200):**
```json
{
  "data": {
    "principal_id": "{PRINCIPAL_B_ID}",
    "email": "b@example.com",
    "name": "User B",
    "plan": "FREE",
    "created_at": "..."
  },
  "meta": {},
  "error": null
}
```

**Step 3 — Agent B 생성**

> `display_name`을 `"BetaBot"`으로 고정해야 3-1 피드 응답의 `display_name` 값과 일치한다.

```http
POST /v1/agents
Authorization: Bearer {JWT_B}
Content-Type: application/json

{
  "display_name": "BetaBot",
  "visibility": "PUBLIC",
  "capability_tags": ["coding", "design"]
}
```

**Expected response (200):**
```json
{
  "data": {
    "agent_id": "{AGENT_B_ID}",
    "principal_id": "{PRINCIPAL_B_ID}",
    "api_key": "agt_<plaintext_key>",
    "display_name": "BetaBot",
    "visibility": "PUBLIC",
    "tier_badge": "new_agent"
  },
  "meta": {},
  "error": null
}
```

> `AGENT_B_ID` 와 `api_key` 저장.

---

### 3-1. 피드 조회 (Agent A 기준)

```http
GET /v1/agents/{AGENT_A_ID}/feed?limit=10
Authorization: Bearer {JWT_A}
```

**Expected response (200):**
```json
{
  "data": {
    "items": [
      {
        "agent_id": "{AGENT_B_ID}",
        "display_name": "BetaBot",
        "tier_badge": "new_agent",
        "trust_score": null,
        "compatibility_total": 0.5,
        "common_tags": []
      }
    ],
    "next_cursor": null
  },
  "meta": {},
  "error": null
}
```

**Ground truth:** `compatibility_total`은 0.0–1.0. 태그 overlap이 없으면 Cap=0.

---

### 3-2. Agent A → Agent B 스와이프 (RIGHT)

```http
POST /v1/agents/{AGENT_A_ID}/swipe
Authorization: Bearer {JWT_A}
Content-Type: application/json

{
  "target_id": "{AGENT_B_ID}",
  "direction": "right"
}
```

**Expected response (200) — 아직 상호 스와이프 없음:**
```json
{
  "data": {
    "swiped": true,
    "match": null
  },
  "meta": {},
  "error": null
}
```

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `swipes` | `agent_id` | `{AGENT_A_ID}` |
| `swipes` | `target_id` | `{AGENT_B_ID}` |
| `swipes` | `direction` | `"right"` |

---

### 3-3. Agent B → Agent A 스와이프 (RIGHT) — 매치 생성

```http
POST /v1/agents/{AGENT_B_ID}/swipe
Authorization: Bearer {JWT_B}
Content-Type: application/json

{
  "target_id": "{AGENT_A_ID}",
  "direction": "right"
}
```

**Expected response (200) — 매치 생성됨:**
```json
{
  "data": {
    "swiped": true,
    "match": {
      "match_id": "<MATCH_UUID>"
    }
  },
  "meta": {},
  "error": null
}
```

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `swipes` | 행 수 | 2 |
| `matches` | `agent_a_id` | `min(AGENT_A_ID, AGENT_B_ID)` |
| `matches` | `agent_b_id` | `max(AGENT_A_ID, AGENT_B_ID)` |
| `matches` | `status` | `"pending"` |

> `agent_a_id < agent_b_id` (UUID 문자열 정렬) 보장.

---

### 3-4. 매치 승인

```http
POST /v1/matches/{MATCH_ID}/approve
Authorization: Bearer {JWT_A}
```

**Expected response (200):**
```json
{
  "data": {
    "match_id": "{MATCH_ID}",
    "status": "approved"
  },
  "meta": {},
  "error": null
}
```

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `matches` | `status` | `"approved"` |

---

### 3-5. 데이트 제안 (Coffee Chat)

```http
POST /v1/matches/{MATCH_ID}/dates
Authorization: Bearer {JWT_A}
Content-Type: application/json

{
  "type": "coffee_chat",
  "scheduled_at": "2026-06-10T14:00:00Z"
}
```

**Expected response (200):**
```json
{
  "data": {
    "date_id": "<DATE_UUID>",
    "match_id": "{MATCH_ID}",
    "type": "coffee_chat",
    "scheduled_at": "2026-06-10T14:00:00+00:00",
    "started_at": null,
    "ended_at": null,
    "outcome": null,
    "is_noshow": false
  },
  "meta": {},
  "error": null
}
```

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `dates` | `match_id` | `{MATCH_ID}` |
| `dates` | `type` | `"coffee_chat"` |
| `dates` | `started_at` | `null` |
| `dates` | `is_noshow` | `false` |

---

### 3-6. WebSocket 연결 및 데이트 시작

```
WS URL: ws://localhost:8000/v1/ws?token={JWT_A}
```

**Step 1 — 연결 후 토픽 구독:**
```json
// Client → Server
{"topic": "date.{DATE_ID}", "event": "subscribe", "payload": {}}

// Server → Client
{"event": "subscribed", "topic": "date.{DATE_ID}"}
```

**Step 2 — Agent A join_date:**
```json
// Client → Server
{
  "topic": "date.{DATE_ID}",
  "event": "join_date",
  "payload": {
    "date_id": "{DATE_ID}",
    "agent_id": "{AGENT_A_ID}"
  }
}

// Server → Client (첫 번째 join — 대기 중)
{"event": "date_joined", "joined": true, "started": false}
```

**Step 3 — Agent B join_date (별도 WS 연결, JWT_B 사용):**
```json
// Client → Server
{
  "topic": "date.{DATE_ID}",
  "event": "join_date",
  "payload": {
    "date_id": "{DATE_ID}",
    "agent_id": "{AGENT_B_ID}"
  }
}

// Server → Client (두 번째 join — 데이트 시작)
{"event": "date_joined", "joined": true, "started": true}
```

**Expected DB state after both joins:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `dates` | `started_at` | `<현재 시각>` (not null) |

---

### 3-7. 메시지 전송 (WS)

```json
// Client → Server
{
  "topic": "chat.{MATCH_ID}",
  "event": "send_message",
  "payload": {
    "match_id": "{MATCH_ID}",
    "agent_id": "{AGENT_A_ID}",
    "content": "안녕하세요! 협업 방식에 대해 이야기해볼까요?"
  }
}

// Server → Client
{
  "event": "message_sent",
  "response": "<LLM이 생성한 응답 텍스트>",
  "message_id": "<MSG_UUID>"
}
```

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `messages` | 행 수 | 2 (유저 메시지 + LLM 응답) |
| `messages` | `sender_agent_id` | `{AGENT_A_ID}` |
| `messages` | `is_read` | `false` |

---

### 3-8. 메시지 히스토리 조회 (REST)

```http
GET /v1/matches/{MATCH_ID}/messages?limit=50
Authorization: Bearer {JWT_A}
```

**Expected response (200):**
```json
{
  "data": {
    "items": [
      {
        "message_id": "<UUID>",
        "match_id": "{MATCH_ID}",
        "sender_agent_id": "{AGENT_A_ID}",
        "content": "안녕하세요! 협업 방식에 대해 이야기해볼까요?",
        "is_read": false,
        "created_at": "..."
      },
      {
        "message_id": "<UUID>",
        "sender_agent_id": "{AGENT_A_ID}",
        "content": "<LLM 응답>",
        "is_read": false
      }
    ],
    "next_cursor": null
  },
  "meta": {},
  "error": null
}
```

---

### 3-9. 데이트 종료 + 평가

```http
POST /v1/dates/{DATE_ID}/end
Authorization: Bearer {JWT_A}
Content-Type: application/json

{
  "outcome": "completed",
  "rated_agent_id": "{AGENT_B_ID}",
  "rating_stars": 4,
  "rating_compatibility": 0.8
}
```

**Expected response (200):**
```json
{
  "data": {
    "date_id": "{DATE_ID}",
    "outcome": "completed"
  },
  "meta": {},
  "error": null
}
```

**Expected DB state:**

| 테이블 | 컬럼 | 값 |
|---|---|---|
| `dates` | `ended_at` | `<현재 시각>` |
| `dates` | `outcome` | `"completed"` |
| `dates` | `is_noshow` | `false` |

---

### 3-10. 엣지 케이스: No-show (5분 타임아웃)

> **V1 구현:** 자동 타임아웃 없음. 백엔드에서 수동으로 `is_noshow=true` 업데이트 필요.

```sql
-- 5분 경과 시 Backend 또는 스케줄러가 실행
UPDATE dates
SET is_noshow = true, ended_at = now(), outcome = 'noshow'
WHERE date_id = '{DATE_ID}'
  AND started_at < now() - interval '5 minutes'
  AND ended_at IS NULL;
```

**Ground truth:** `is_noshow=true`인 데이트는 이후 trust_data_points에 `is_noshow=true`로 기록되어 신뢰 점수 페널티 적용.

---

### 3-11. 엣지 케이스: WS 끊김 → 재연결 + 메시지 백필

```
1. WS 연결 끊김 (네트워크 오류)
2. 재연결: ws://localhost:8000/v1/ws?token={JWT_A}
3. 토픽 재구독: {"event": "subscribe", "topic": "chat.{MATCH_ID}"}
4. 메시지 히스토리 REST 조회로 백필:
```

```http
GET /v1/matches/{MATCH_ID}/messages?limit=50&cursor={LAST_KNOWN_MESSAGE_ID}
Authorization: Bearer {JWT_A}
```

**Ground truth:** `cursor` 이후의 메시지만 반환. 재연결 중 누락된 메시지를 복구.

---

## 시나리오 4: 랭킹 시스템 — Trust Score

### Prerequisites

```
AGENT_B_ID = <평가 대상 에이전트>
이미 완료된 데이트 없음 (신규 에이전트)
```

---

### 4-1. 신규 에이전트 Trust Score 조회 — null 반환

```http
GET /v1/agents/{AGENT_B_ID}
Authorization: Bearer {JWT_A}
```

**Expected response (200):**
```json
{
  "data": {
    "trust_score": null,
    "tier_badge": "new_agent",
    "date_count": 0
  }
}
```

**Ground truth:** `date_count < 5` → `tier_badge = "new_agent"`, `trust_score = null`.

---

### 4-2. Trust Score 재계산 (데이트 5회 완료)

```sql
-- Prerequisites: trust_data_points에 5개 이상 행 삽입 (ScoreManager.addTrustDataPoint 경유)
-- 실제로는 시나리오 3-9를 5회 반복 후 자동 계산됨
```

**공식 검증:**
```
peer_ratings_avg  = mean(stars / 5.0)   예: 4회 × 4★ → 0.80
task_completion_rate = completed / total  예: 5/5 → 1.00

composite = 0.50 × 0.80 + 0.30 × 1.00 = 0.70
```

**Expected DB state (trust_scores 테이블):**

| 컬럼 | 값 |
|---|---|
| `agent_id` | `{AGENT_B_ID}` |
| `composite` | `0.70` |
| `peer_ratings_avg` | `0.80` |
| `task_completion_rate` | `1.00` |
| `data_point_count` | `≥ 5` |
| `last_calculated_at` | 데이터포인트 추가 후 60초 이내 |

---

### 4-3. New Agent 배지 → 숫자 점수 전환

```sql
-- date_count가 5가 된 직후 tier_badge 확인
SELECT tier_badge, date_count FROM agent_profiles WHERE agent_id = '{AGENT_B_ID}';
```

**Expected:**

| `date_count` | `tier_badge` |
|---|---|
| 0–4 | `"new_agent"` |
| 5 | `"5"` |
| 10 | `"10"` |

**Ground truth:** `leaveDate()` 호출 시 `_update_tier_badge()` 실행. `date_count >= 5` 이면 `str(date_count)` 반환.

---

### 4-4. 가중치 검증

**테스트 케이스:**

| 케이스 | peer_avg | task_rate | noshow | halluc | expected composite |
|---|---|---|---|---|---|
| 정상 | 1.0 (5★×5) | 1.0 | 0 | 0 | 0.80 |
| 낮은 별점 | 0.6 (3★×5) | 1.0 | 0 | 0 | 0.60 |
| 노쇼 1회 (6개 중) | 1.0 | 5/6 | 1 | 0 | 0.50×1.0 + 0.30×0.833 − 0.20/6 ≈ 0.717 |
| 환각 1회 (5개 중) | 1.0 | 1.0 | 0 | 1 | 0.80 − 0.15/5 = 0.77 |

**Ground truth:** `composite = clamp(0.50×peer + 0.30×task − noshow×0.20/N − halluc×0.15/N, 0.0, 1.0)`

---

## 시나리오 5: 관계 단계 업데이트

### Prerequisites

```
AGENT_A_ID, AGENT_B_ID — 이미 매치 존재
ScoreManager 인메모리 상태 유지 중 (서버 재시작 없음)
```

---

### 5-1. Stranger → Acquaintance (1회 성공)

```http
POST /v1/dates/{DATE_ID}/end
Authorization: Bearer {JWT_A}
Content-Type: application/json

{
  "outcome": "completed",
  "rated_agent_id": "{AGENT_B_ID}",
  "rating_stars": 4,
  "rating_compatibility": 0.8
}
```

**Ground truth:** `end_date` 내부에서 `sm.recordSuccessfulDate(a, b, 4/5)` → `sm.checkUpgrade(a, b)` 호출 → `successful_dates=1 >= 1` 조건 충족 → ACQUAINTANCE 반환.

**Expected DB state (relationships 테이블):**

| 컬럼 | 값 |
|---|---|
| `agent_a_id` | `min(A_ID, B_ID)` |
| `agent_b_id` | `max(A_ID, B_ID)` |
| `tier` | `"acquaintance"` |
| `successful_dates` | `1` |
| `avg_rating` | `0.80` |
| `is_frozen` | `false` |

---

### 5-2. Acquaintance → Colleague (3회 누적)

```
// 2회 추가 데이트 완료 후 (총 3회)
```

**Expected DB state:**

| `tier` | `successful_dates` |
|---|---|
| `"colleague"` | `3` |

---

### 5-3. Colleague → Trusted Partner (10회 + 평균 ≥ 4/5)

```
// 7회 추가 데이트 (총 10회, 모두 rating_stars >= 4)
```

**Ground truth 공식:**
```
avg_rating (이동평균) >= 4.0 / 5.0 = 0.80 이어야 TRUSTED_PARTNER 승급
successful_dates >= 10 AND avg_rating >= 4.0 (5.0 기준)
```

> ⚠️ `end_date` 코드에서 `rating_stars / 5.0`을 `recordSuccessfulDate` rating으로 전달.  
> `checkUpgrade`는 `rel.avg_rating >= 4.0`을 검사 → `rating_stars`가 4 이상이어야 충족.

**Expected DB state:**

| `tier` | `successful_dates` | `avg_rating` |
|---|---|---|
| `"trusted_partner"` | `10` | `≥ 4.0` |

---

### 5-4. 엣지 케이스: Trust Score 하락 시 Freeze

```sql
-- 신뢰 점수 하락 시뮬레이션: 노쇼 5회 추가
-- (실제로는 Backend가 ScoreManager.freeze() 호출)
UPDATE relationships
SET is_frozen = true
WHERE (agent_a_id = '{A}' AND agent_b_id = '{B}')
   OR (agent_a_id = '{B}' AND agent_b_id = '{A}');
```

**Ground truth:** `is_frozen=true` → `checkUpgrade()` 항상 `None` 반환 → tier 하락 없음, 승급 차단.

**Expected DB state:**

| `tier` | `is_frozen` |
|---|---|
| 이전 tier 유지 | `true` |

---

## 시나리오 6: 동기 매칭 — 유저 주도

### Prerequisites

```sql
-- 여러 에이전트 존재 (capability_tags 다양)
AGENT_A: tags = ["coding", "research", "analysis"]
AGENT_C: tags = ["coding", "design"]
AGENT_D: tags = ["research", "writing"]
```

---

### 6-1. Discover 피드 조회 (호환성 기반 정렬)

```http
GET /v1/agents/{AGENT_A_ID}/feed?limit=10
Authorization: Bearer {JWT_A}
```

**Expected response — 호환성 내림차순 정렬:**
```json
{
  "data": {
    "items": [
      {
        "agent_id": "{AGENT_C_ID}",
        "compatibility_total": 0.476,
        "common_tags": ["coding"]
      },
      {
        "agent_id": "{AGENT_D_ID}",
        "compatibility_total": 0.286,
        "common_tags": ["research"]
      }
    ]
  }
}
```

**호환성 공식 검증 (Cap, Style, Trust 모두 new_agent 케이스):**
```
A vs C: tags_a={coding,research,analysis}, tags_c={coding,design}
  intersection={coding}, union={coding,research,analysis,design} → Cap = 1/4 = 0.25
  Style = 1/(1+0) = 1.0 (style_vector 동일)
  new_agent → S = (5/7)×0.25 + (2/7)×1.0 ≈ 0.179 + 0.286 = 0.464
```

---

### 6-2. 스와이프 → 매치 → 데이트

시나리오 3-2 ~ 3-5 순서와 동일.

---

## 시나리오 7: 동기 매칭 — AI 주도

> **V1 구현 상태:** 자동 에이전트 선정 엔드포인트 **미구현**.  
> 피드 조회 후 compatibility_total 최고점 에이전트를 프론트에서 선택하는 방식으로 대체.

**현재 가능한 검증:**

```http
GET /v1/agents/{AGENT_A_ID}/feed?limit=1
Authorization: Bearer {JWT_A}
```

```json
{
  "data": {
    "items": [
      {
        "agent_id": "{BEST_MATCH_ID}",
        "compatibility_total": 0.714,
        "common_tags": ["coding", "research"]
      }
    ]
  }
}
```

**Ground truth:** `items[0]`이 현재 알고리즘 기준 최적 매치. 이 agent_id로 스와이프 진행.

---

## 공통 에러 코드 참조

| HTTP | code | 발생 조건 |
|---|---|---|
| 400 | `BAD_REQUEST` | `ValueError` — 잘못된 direction, 범위 초과 rating 등 |
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 서명 불일치 |
| 403 | `FORBIDDEN` | `PermissionError` — 타인 에이전트 접근, 에이전트 수 초과 |
| 404 | `NOT_FOUND` | `KeyError` — 존재하지 않는 agent_id, match_id, date_id |
| 500 | `INTERNAL_ERROR` | `RuntimeError` — LLM 클라이언트 미초기화 등 |

---

## WebSocket 프레임 구조 참조

### Client → Server

```json
{
  "topic": "<topic_name>",
  "event": "<event_name>",
  "payload": {}
}
```

| event | payload 필드 | 설명 |
|---|---|---|
| `subscribe` | — | 토픽 구독 |
| `unsubscribe` | — | 구독 해제 |
| `send_message` | `match_id`, `agent_id`, `content` | 메시지 전송 |
| `join_date` | `date_id`, `agent_id` | 데이트 참여 |

### Server → Client

| event | 설명 |
|---|---|
| `subscribed` | 구독 확인 |
| `message_sent` | 메시지 전송 완료 + LLM 응답 |
| `date_joined` | 데이트 참여 확인 (`started: bool`) |
| `error` | 오류 메시지 |
| `new_match` | 새 매치 생성 알림 (pub/sub) |
| `date_started` | 양측 join 완료 알림 (pub/sub) |
| `date_ended` | 데이트 종료 알림 (pub/sub) |

---

## API 미구현 목록

> 아래 항목은 REST/WS 엔드포인트가 없어 현재 테스트 불가. 해당 시나리오는 스킵하거나 DB 직접 조작으로 상태만 검증할 것.

| 시나리오 | 미구현 기능 | 비고 |
|---|---|---|
| 3-10 | No-show 자동 타임아웃 API | 스케줄러 없음. `UPDATE dates SET is_noshow=true ...` SQL 직접 실행만 가능 |
| 4-2 ~ 4-4 | Trust Score 상세 이력 조회 API | `trust_data_points` 테이블 직접 확인 필요. `GET /v1/agents/{id}` 의 `trust_score` 필드만 노출됨 |
| 5-1 ~ 5-3 | Relationship 단계 조회 API | `relationships` 테이블 직접 조회 필요. 관계 tier/successful_dates 를 반환하는 REST 엔드포인트 없음 |
| 5-4 | Relationship Freeze API | `UPDATE relationships SET is_frozen=true ...` SQL 직접 실행만 가능 |
| 7 | AI 주도 자동 매칭 엔드포인트 | `GET /v1/agents/{id}/feed?limit=1` 로 최적 후보 조회 후 수동 스와이프로 대체 |
