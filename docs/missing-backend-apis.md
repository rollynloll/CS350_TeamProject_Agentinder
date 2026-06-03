# 미구현 백엔드 API 명세

작성: 2026-06-03 (팀원 D — 프론트엔드)
기준 백엔드 커밋: `c331e3d` (`Merge #14`) — `GET http://localhost:8000/openapi.json` 16 path

프론트 14개 화면이 호출하는 API와 백엔드 OpenAPI를 1:1 대조한 결과, 화면은 띄워졌지만 **백엔드 라우트가 없거나 메서드가 다른** 항목을 모았다. SRS 참조번호는 확인된 것만 표기.

---

## 0. 요약 (우선순위)

| 우선 | 메서드 + 경로 | 막힌 화면 | SRS / 결정 |
|:---:|---|---|---|
| 🔴 High | `GET /v1/agents/{agent_id}/analytics` | `/analytics` (AnalyticsPage) — 빈 차트 | REQ-0507, CO-5 |
| 🔴 High | `GET /v1/agents/{agent_id}/relationships` | `/relationships` (RelationshipsPage) — 빈 리스트 | REQ-0606 |
| 🔴 High | `GET /v1/principals/me/settings` + `PATCH /v1/principals/me/settings` | `/settings` 및 6개 서브페이지 전부 — 빈 데이터 | REQ-0607/0608, REQ-0303 |
| 🟡 Mid | `POST /v1/agents/{agent_id}/avatar` (multipart) | ProfileForm 아바타 업로드 — 시각만 동작 | REQ-0102 |
| 🟡 Mid | `POST /v1/principals/me/api-keys` + `DELETE /v1/principals/me/api-keys/{key_id}` | `/settings/api-keys` 액션 버튼 무동작 | REQ-0303 |
| 🟢 Low | `DELETE /v1/agents/{agent_id}` | 에이전트 삭제 UI 미구현 (FE 호출만 정의됨) | REQ-0104 |
| 🟢 Low | `PATCH /v1/dates/{date_id}` (상태 변경) | DateLivePage 상태 갱신 (현재 POST `/end`로만 종료 가능) | — |

추가로 **메서드/경로 미스매치** 1건과 **백엔드 있는데 프론트가 안 부르는 경우** 1건이 별도 섹션에 있음 (백엔드 구현은 OK).

---

## 1. `GET /v1/agents/{agent_id}/analytics`

**목적**: AnalyticsPage의 5개 섹션 데이터 일괄 조회 (Trust 추이 / Date 성공률 / Top capability / Tier 성장 / Best partner)

**Path params**
- `agent_id` (UUID, required) — 분석 대상 에이전트. AuthorizationPolicy: 호출자 principal이 소유한 agent여야 함.

**Query params** (optional)
- `since` (ISO date, default = -90d) — 추이 그래프 시작
- `until` (ISO date, default = now)

**Response** — frontend [AnalyticsResponse](../frontend/src/api/types.ts) 와 호환되어야 함 (필드명은 snake_case로 보내고 adapter가 camelCase 변환)
```jsonc
{
  "data": {
    "trust_score_trend": [
      { "date": "2026-04-01", "score": 0.82 }
    ],
    "date_stats": {
      "total_dates": 18,
      "success_rate": 0.78,
      "by_type": {
        "coffee_chat":   { "count": 12, "success_rate": 0.83 },
        "activity_date": { "count": 4,  "success_rate": 0.75 },
        "deep_dive":     { "count": 2,  "success_rate": 0.5  }
      }
    },
    "compatibility_breakdown": {
      "top_domains": [
        { "domain": "research", "avg_score": 0.91 }
      ],
      "style_match_rate": 0.73
    },
    "relationship_growth": [
      {
        "date": "2026-05-01",
        "stranger": 8, "acquaintance": 5, "colleague": 2, "trusted_partner": 1
      }
    ],
    "relationship_summary": {
      "total_relationships": 15,
      "by_tier": { "stranger": 5, "acquaintance": 6, "colleague": 3, "trusted_partner": 1 },
      "recent_activity": [
        {
          "match_id": "uuid",
          "partner_display_name": "Scheduler",
          "partner_avatar_url": "...",
          "tier": "acquaintance",
          "last_interaction_at": "2026-05-09T18:00:00Z",
          "mutual_rating": 4.2
        }
      ]
    }
  },
  "meta": {}, "error": null
}
```

**Auth**: Bearer JWT 필수, agent 소유권 검증
**Idempotency**: 읽기 전용 — 불필요

---

## 2. `GET /v1/agents/{agent_id}/relationships`

**목적**: RelationshipsPage에서 매칭된 상대 에이전트를 **tier 기준으로 그룹화**해 표시

**Path params**: `agent_id` (UUID)
**Query params** (optional):
- `tier` — `stranger | acquaintance | colleague | trusted_partner` 단일 필터
- `limit` (default 50, max 100), `cursor`

**Response**
```jsonc
{
  "data": {
    "groups": [
      {
        "tier": "acquaintance",
        "count": 5,
        "relationships": [
          {
            "match_id": "uuid",
            "partner_agent": {
              "agent_id": "uuid",
              "display_name": "Scheduler",
              "avatar_url": "...",
              "trust_score": 0.92
            },
            "tier": "acquaintance",
            "total_dates": 2,
            "last_date_at": "2026-04-20T15:00:00Z",
            "mutual_rating": 4.2,
            "last_date_summary": "Coffee Chat — discussed scheduling"
          }
        ]
      }
    ],
    "total_relationships": 15
  }
}
```

**Auth**: Bearer + 소유권
**참고**: 백엔드 `relationships` 테이블 + `agents` join 필요 (Score Service의 tier 계산)

---

## 3. Settings: `GET / PATCH /v1/principals/me/settings`

**목적**: SettingsPage(메인 + 서브 6개)의 데이터 + 변경 mutation

### 3a. `GET /v1/principals/me/settings`

**Response** — frontend [SettingsResponse](../frontend/src/api/types.ts) 미러링
```jsonc
{
  "data": {
    "account": {
      "email": "user@example.com",
      "display_name": "John Doe",
      "created_at": "2026-01-15T10:00:00Z"
    },
    "api_keys": [
      {
        "key_id": "uuid",
        "name": "Production",
        "last_used_at": "2026-05-09T18:00:00Z",
        "created_at": "2026-03-01T10:00:00Z"
      }
    ],
    "notifications": {
      "match_alerts":    true,
      "date_reminders":  true,
      "weekly_digest":   true,
      "message_preview": true
    },
    "preferences": {
      "global_trust_threshold": 0.5,
      "auto_match_rules": {
        "enabled":           false,
        "min_compatibility": 0.8,
        "min_trust":         0.7
      }
    },
    "privacy": {
      "profile_visibility":      "public",        // public | restricted | hidden
      "date_transcript_sharing": "mutual_consent", // mutual_consent | owner_only | platform
      "analytics_opt_in":        true
    }
  }
}
```

### 3b. `PATCH /v1/principals/me/settings`

**Body** (partial update — 모든 키 optional, 보낸 키만 갱신)
```jsonc
{
  "notifications": { "weekly_digest": false },
  "preferences": {
    "global_trust_threshold": 0.6,
    "auto_match_rules": { "enabled": true }
  },
  "privacy": { "profile_visibility": "restricted" }
}
```

**Response**: 갱신된 `SettingsResponse` 전체 (편의상). 또는 변경분만 + 200.

**Idempotency**: `X-Idempotency-Key` 헤더 (FE가 자동 부여)
**Auth**: Bearer JWT — `account` 슬라이스는 JWT의 principal 정보 사용

---

## 4. API key 발급/회수

### 4a. `POST /v1/principals/me/api-keys`

**Body**
```jsonc
{ "name": "Production" }  // 사용자가 라벨 입력
```

**Response** — **이번 한 번만 평문 키 노출**(REQ-0105의 credential 흐름과 동일)
```jsonc
{
  "data": {
    "key_id": "uuid",
    "name": "Production",
    "api_key": "ak_live_…",     // 절대 다시 안 보여줌
    "created_at": "2026-06-03T..."
  }
}
```

### 4b. `DELETE /v1/principals/me/api-keys/{key_id}`

**Response**
```jsonc
{ "data": { "key_id": "uuid", "revoked_at": "2026-06-03T..." } }
```

**Auth**: Bearer; 호출자가 그 키의 소유 principal이어야 함
**저장**: 해시 저장 권장 (revoke = 단순 삭제 또는 `revoked_at` 컬럼)

---

## 5. `POST /v1/agents/{agent_id}/avatar` (multipart)

**목적**: ProfileForm의 아바타 이미지 업로드

**Headers**: `Content-Type: multipart/form-data` (FE는 `FormData`로 보냄)
**Body**: 필드명 `file` — 5 MB 제한, MIME `image/jpeg|png|webp` (REQ-0102)

**Response**
```jsonc
{ "data": { "avatar_url": "https://storage…/avatars/<agent_id>.webp" } }
```

**Errors**
- 413 — 5MB 초과 (`code: "PAYLOAD_TOO_LARGE"`)
- 415 — 미지원 MIME (`code: "UNSUPPORTED_MEDIA_TYPE"`)

**Auth**: Bearer + agent 소유권
**저장**: Supabase Storage 권장 — bucket `avatars/`, public read

---

## 6. `DELETE /v1/agents/{agent_id}` (낮은 우선순위)

**목적**: 에이전트 영구 삭제. 프론트엔 호출 코드만 정의(`endpoints/agents.ts`), 화면 진입점은 미구현 — 백엔드만 만들어두면 UI는 별도 티켓.

**Response**
```jsonc
{ "data": { "agent_id": "uuid", "deleted_at": "2026-06-03T..." } }
```

**Cascade**: matches/messages/dates는 ON DELETE CASCADE FK로 처리하거나 soft delete 결정 필요 (팀 A·B 협의)
**Auth**: Bearer + 소유권

---

## 7. `PATCH /v1/dates/{date_id}` (낮은 우선순위)

**목적**: 데이트 상태 변경 — 현재 `POST /v1/dates/{id}/end` 외에 일반 상태 변경 API가 없어 FE의 `useUpdateDate` 같은 mutation이 동작 안 함.

**Body**
```jsonc
{ "status": "in_progress" }   // proposed → in_progress | cancelled | no_show 등
```

**참고**: 도메인적으로 `POST .../end` + `POST .../start`로 분리하는 게 깔끔할 수 있음. FE/팀 B 협의 후 결정.

---

## 8. 별도 — 백엔드 OK인데 프론트가 안 부르는 케이스

### `GET /v1/agents/{agent_id}/discover` 가 있음에도 안 씀

- 백엔드: ✅ 16개 라우트에 포함
- 프론트: `useDiscover` 훅이 **MIGRATE 분기 없이** `GET /v1/discover/{agentId}` 한 경로만 호출 → real 모드에서 404
- **프론트 수정사항**:
  1. `migration-flags.ts`에 `discover` 키 추가
  2. `endpoints/discover.ts` 훅에 `MIGRATE.discover ? api.get("/agents/{id}/discover", ...).then(adapt) : api.get("/discover/{id}", ...)` 분기
  3. 어댑터 (`adapters/discover.adapter.ts`) 신설 — 백엔드 응답 형태 확인 후

→ 본 문서는 백엔드 미구현 위주라 이 항목은 FE 후속 티켓.

---

## 9. 메서드 미스매치 (백엔드는 OK)

| 화면 | FE 호출 | BE 실제 |
|---|---|---|
| Agent 프로필 수정 | `PUT /v1/agents/{id}/profile` (mock 분기) → MIGRATE 켜진 분기는 `PATCH /v1/agents/{id}` 이미 맞춤 | `PATCH /v1/agents/{id}` ✅ |

→ FE 어댑터가 이미 PATCH로 변환해서 보냄. 백엔드 작업 불필요.

---

## 10. WebSocket — 메시지 전송 (참고)

REST는 아니지만 같은 인증 + 토픽 구조라 한 줄 정리:
- **`event: "send_message"`** WS action — 백엔드 [`ws_transport._dispatch`](../backend/app/transport/ws_transport.py) + [`handle_send_message`](../backend/app/handlers/message_handler.py) 완전 구현 ✅
- 단 한 가지 quirk(별건): 에이전트 자동응답이 `sender_agent_id=sender_agent_id` (보낸 본인)로 저장됨 → 프론트에선 "내 메시지"로 렌더됨. 응답을 partner agent로 저장하든지, 별도 `agent_reply_id`를 두든지 결정 필요.

---

## 부록 A — FE↔BE 전체 매핑 (참고)

| FE (의도) | 백엔드 path | 상태 |
|---|---|---|
| 회원 보장 | `POST /v1/principals` | ✅ |
| Agent 목록 | `GET /v1/agents` | ✅ |
| Agent 생성 | `POST /v1/agents` | ✅ |
| Agent 상세 | `GET /v1/agents/{id}` | ✅ |
| Agent 수정 | `PATCH /v1/agents/{id}` | ✅ |
| Agent 삭제 | `DELETE /v1/agents/{id}` | ❌ §6 |
| Avatar 업로드 | `POST /v1/agents/{id}/avatar` | ❌ §5 |
| Feed | `GET /v1/agents/{id}/feed` | ✅ |
| Swipe | `POST /v1/agents/{id}/swipe` | ✅ |
| Discover | `GET /v1/agents/{id}/discover` | ✅ (FE 미연결) |
| Analytics | `GET /v1/agents/{id}/analytics` | ❌ §1 |
| Relationships | `GET /v1/agents/{id}/relationships` | ❌ §2 |
| Matches | `GET /v1/matches?agent_id=...` | ✅ |
| Match 승인 | `POST /v1/matches/{id}/approve` | ✅ |
| Match 거절 | `POST /v1/matches/{id}/reject` | ✅ |
| Date 이력 | `GET /v1/matches/{id}/dates` | ✅ |
| Date 제안 | `POST /v1/matches/{id}/dates` | ✅ |
| Date 조회 | `GET /v1/dates/{id}` | ✅ |
| Date 상태 PATCH | `PATCH /v1/dates/{id}` | ❌ §7 |
| Date 종료 + 평가 | `POST /v1/dates/{id}/end` | ✅ |
| 메시지 목록 | `GET /v1/matches/{id}/messages` | ✅ |
| 메시지 송신 | WS `send_message` | ✅ |
| Settings 조회 | `GET /v1/principals/me/settings` | ❌ §3a |
| Settings 갱신 | `PATCH /v1/principals/me/settings` | ❌ §3b |
| API key 발급 | `POST /v1/principals/me/api-keys` | ❌ §4a |
| API key 회수 | `DELETE /v1/principals/me/api-keys/{id}` | ❌ §4b |
| Auth | `POST /v1/auth/{login,refresh,logout}` | ✅ |

---

## 부록 B — 작업 분할 권장

1. **3a/3b (Settings GET/PATCH)** — 가장 많은 화면(6개 서브)을 한번에 살림. SRS Privacy/Notifications/Trust Threshold/Auto-match 모두 의존.
2. **1 (Analytics) + 2 (Relationships)** — 데이터 집계 쿼리만 잘 짜면 됨. 둘 다 SRS Score/Relationship 도메인 활용.
3. **5 (Avatar 업로드)** — Storage 연동 한 번만 하면 향후 다른 미디어에도 재사용.
4. **4 (API keys)** — 평문 노출이 1회뿐인 흐름이라 Credential 모달(REQ-0105)과 동일 패턴 재사용 가능.

각각 백엔드 PR 단위로 분리 권장. 프론트는 어댑터 + MIGRATE 플래그만 추가하면 즉시 연결.
