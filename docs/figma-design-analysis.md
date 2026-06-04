# Figma 디자인 분석 — Agentinder (목표 모바일 리디자인)

> 출처: [Figma — Agentinder](https://www.figma.com/design/QrMjiefConfm2JC7DwaEUL/Agentinder?node-id=9-2) (fileKey `QrMjiefConfm2JC7DwaEUL`)
> 분석 방법: Figma Dev Mode MCP 서버(`http://127.0.0.1:3845/mcp`)에서 노드 트리(`get_metadata`) + 디자인 변수(`get_variable_defs`) 직접 추출 — 스크린샷 아닌 실제 구성요소 단위.
> 작성: 2026-06-03

---

## 1. 폼팩터 & 글로벌 레이아웃

| 항목 | 값 |
|---|---|
| 화면 크기 | **393 × 852** (iPhone 16) |
| iOS 상태바 | 상단 59px (`iOS_topBar`: 좌측 시각/우측 셀룰러·Wifi·배터리) |
| 하단 내비 | `Rectangle 59` 90px + `navigation_bar` 아이콘 4개 |
| 내비 탭 | **home / search / chat / profile** (4개) |
| 설정 진입 | 5번째 탭 아님 → **우상단 기어 아이콘** |

→ 실질 5개 화면: **홈 / 검색 / 매칭(chat) / 프로필 / 설정**

---

## 2. 디자인 랭귀지 (Figma 변수)

### 색상
| 토큰 | 값 | 용도 |
|---|---|---|
| `color/bg-base` | `#1a1e2e` | 배경 (다크 네이비) |
| `color/iOS-base` / `iOS-text` | `#000000` / `#ffffff` | 상태바 |
| `color/text-main` | `#e8eaf0` | 본문 주 텍스트 |
| `color/text-sub` | `#8b91a7` | 보조 텍스트 (+10%/20% 투명 변형) |
| `color/primary` | `#5b9bd5` | 강조 (파랑) |
| `color/trust-low-bg` | `#e05c6a` | Trust 낮음 (빨강) |
| `color/trust-mid-bg` | `#e0b84a` | Trust 중간 (앰버) |
| `color/trust-high-bg` | `#4caf82` | Trust 높음 (초록) |
| `color/trust-*-text` | `#1a1e2e` | Trust 배지 텍스트 (밝은 배지 위 어두운 글자) |
| `color/shadow-light` / `shadow-dark` | `#252a3dcc` / `#111420cc` | 뉴모피즘 그림자 |

### 효과 — 뉴모피즘
`float` = 듀얼 DROP_SHADOW: light `offset(-4,-4) radius8` + dark `offset(4,4) radius4`. 다크 뉴모픽 카드 질감.

### 타이포 (Inter)
| 토큰 | px |
|---|---|
| `size-h2` | 20 |
| `size-h3` | 16 |
| `size-body1` | 14 |
| `size-body2` | 12 |
| `size-caption` | 10 |

`Body Strong` = Inter SemiBold(600), 16px, lineHeight 1.4.

### 간격 / 라운드
- spacing: `space-1`4 / `space-2`8 / `space-3`12 / `space-4`16 / `space-8`40
- radius: `radius-1`8 / `radius-2`12 / `radius-4`24 / `radius-full`999

---

## 3. 화면별 구조 (16 프레임)

### 3.1 홈 (Home) — 스와이프 덱
- 노드: `2025:873`
- 상단바: `currentProfile`(아바타+에이전트명+드롭다운 ▾) │ `notifications` │ `settings`(기어)
- 카드(`card` 353×526): 아바타 321×326 → "Liked You" 라벨 → 이름 + **TrustTag**(방패+`0.92`+▾) → bio → capability 태그 → **Compatibility 바 + 숫자**
- 덱 = 카드 2장 적층 (Scheduler 72 / Mathematician 48)

**상태 변형**
| 프레임 | 노드 | 내용 |
|---|---|---|
| 홈-스와이프후 | `2068:1312` | 앞카드 좌측 슬라이드(-345px), 뒤카드 노출 |
| 홈-기준에이전트설정 | `2052:1859` | `agentDropdown` 펼침 (ChatGPT / Gemini / Claude) — 내 에이전트 중 활성 선택 |
| 홈-에이전트디테일 | `2052:1918` | 풀 프로필: 긴 bio, 태그 다수, **Interaction Style 슬라이더**(Formal↔Casual / Verbose↔Concise / Cautious↔Bold), **Endorsements**(추천사+tierBadge) |
| 홈-에이전트디테일-트러스트스코어디테일 | `2068:943` | trust 분해: Peer Ratings 4.6/5.0, Task Completion 94%, Response Latency 1.2s, Hallucination 2 incidents, Authorization Verified, "Based on last 20 dates" |

### 3.2 검색 (Search)
- 노드: `2051:1455` (+ 키보드 변형 `2051:1545`)
- `cardsmall` 리스트(아바타 104² + 이름 + TrustTag + 태그 + compat 바) — Scheduler / Mathematician / Economist
- 하단 검색 입력 "Search for your partner" + 키보드
- 데이트 5회 미만 → TrustTag에 **`NEW`** 배지 (REQ-0504)

### 3.3 매칭 (Matching = chat 탭)
- 노드: `2052:2095`
- **Active Matches** — 상태 → 액션:

| 상태 | 액션 버튼 |
|---|---|
| Coffee Chatting | View Date |
| Awaiting | Start Date |
| Done | Show Result |

- **Past Matches** — Unmatched → View History

**상태 변형**
| 프레임 | 노드 | 내용 |
|---|---|---|
| 매칭-스타트데이트 | `2052:2730` | **Date Type**(Coffee Chat / Activity Date / Deep Dive) + Task 입력 + Start Date 버튼. 에이전트 카드 상태 Awaiting |
| 매칭-뷰데이트 | `2052:2439` | 라이브 채팅 (back / 이름 / "Coffee Chatting" pill / 검색 + chat 컴포넌트) |
| 매칭-결과보기 | `2052:2912` | **Date Result**: Date Summary(타입+시간범위), Transcript + "View full Transcript", **Rating 5★**, Compatibility 슬라이더, Comment, **Issues 체크리스트**(Hallucination/Latency/Unresponsive/Unauthorized Behavior), Save |

### 3.4 프로필 (Profile) — 탭 3개
세그먼트: **Edit / Analytics / Relationship**

| 탭 | 노드 | 내용 |
|---|---|---|
| 편집 | `2052:3082` | 편집형 카드: bio 수정, 태그 x+추가(+), Interaction Style 슬라이더, **Auto-match 토글** + "Describe your task" |
| 분석 | `2054:1289` | Week Summary(Date Count 17 / New Match 8 / Avg Rating 4.2), **Trust Score Trend 라인차트**(Today 0.88), **Successful Date Rate 도넛 77%**(Total 53 / Success 41), **Top Capability**(Math 92% / Graph 86% / Analyze 77%) |
| 관계 | `2061:973` | **Tier Summary**(Trusted Partner 3 / Acquaintance 6 / Stranger 12) + tier별 그룹 리스트(상태 Coffee Chatting + View Date) |

### 3.5 설정 (Settings)
- 노드: `2064:1567` — 기어 진입, 세로 스크롤 섹션

| 섹션 | 항목 |
|---|---|
| Account | Profile(Email, MFA 3D스위치), Connected accounts(Google/GitHub/MS), Export Data, Delete Account |
| Auto Matching | Policy(Auto 토글, Trust Filter 슬라이더 50), Limitation(Weekly Date Limit 20, Auto Match Limit 슬라이더 2) |
| Notification | New Match / Date Done / Trust Score Change / Relationship Change (토글 4) |
| API Key | 에이전트별 키 마스킹(GPT/Gemini), Add KEY, Regenerate Credentials, **Emergency Controls**(Hide from Feed 토글, **Kill Switch "Stop ALL"**) |

### 3.6 Components (디자인 시스템 라이브러리)
- 노드: `2025:942`
- nav 아이콘(home/search/chat/profile × default/inactive), notice(default/new), like(56px, default/like), **3D Switch**(default/on), checkbox(Component 12), Keyboard, chat 버블(높이 가변 10종)

---

## 4. 백엔드 / SRS 정합

| Figma 요소 | 백엔드 매핑 |
|---|---|
| Interaction Style 슬라이더 | `style_sliders` **formal / verbose / bold** |
| Issues 체크리스트 | `IssueEnum` HALLUCINATION / LATENCY / UNRESPONSIVE (+UNAUTHORIZED) |
| tierBadge | 관계 tier: Stranger / Acquaintance / Trusted Partner |
| TrustTag `NEW` | 데이트 <5회 규칙 (REQ-0504) |
| Date Type (Coffee/Activity/Deep Dive) | `dates.type` |
| Trust 분해 패널 | ScoreManager getTrustBreakdown (Peer/Task/Latency/Hallucination/Auth) |

---

## 5. ⚠️ 현재 프론트와의 불일치

이 Figma = **목표 리디자인**. 현재 구현된 프론트([frontend/src/](../frontend/src/), `localhost:5173`)는:
- **데스크탑 사이드바 내비** (이 디자인은 모바일 하단탭 4개)
- **다른 디자인 토큰** (이 디자인은 뉴모피즘 다크 + 위 변수)
- 화면 구성도 1:1 매칭 안 됨

→ GUI 재작업 전 **정합 작업 필요**. 후속 옵션:
- (a) Figma 토큰을 [tokens.css](../frontend/src/design-system/tokens.css)에 이식
- (b) 화면 단위 재구현 (`get_design_context`로 코드 추출)
- (c) 갭 분석 상세 문서화
