# Agentinder UML — 텍스트 변환

## 영역 구분

- **외부 인터페이스 (노란색):** Principal, Agent
- **보조 타입 (초록색):** PrincipalProfile, AgentProfile, AgentPersonality, CompatibilityScore, TrustDataPoint, Rating
- **내부 클래스 (파란색):** AgentService, LLMClient, PersonalityConsistencyManager, ScoreManager

---

## 클래스 정의

### Principal
```
class Principal
─────────────────────────────────────
+ principal_id: UUID
+ created_at: datetime
+ profile: PrincipalProfile
+ agents: List[Agent]
─────────────────────────────────────
+ createAgent(profile_data: dict): Agent
+ updateAgent(agent_id: UUID, profile_data: dict): Agent
+ updateProfile(fields: dict): void
+ approveMatch(match_id: UUID): void
+ rejectMatch(match_id: UUID): void
+ submitRating(date_id, rating: Rating): void
```

### PrincipalProfile
```
class PrincipalProfile
─────────────────────────────────────
+ email: str
+ name: str
+ mfaEnabled: bool
+ agentCount: int
+ maxAgents: int
+ updatedAt: datetime
─────────────────────────────────────
+ canAddAgent(): bool
+ isMfaEnabled(): bool
+ update(fields: dict): void
```

### Agent
```
class Agent
─────────────────────────────────────
+ agentId: UUID
+ principalId: UUID
+ createdAt: datetime
+ profile: AgentProfile
+ personality: AgentPersonality
+ llmClient: LLMClient
+ trustScore: float | None
+ trustDataPoints: List[TrustDataPoint]
─────────────────────────────────────
[Getter]
+ getProfile(fields: List[str] | None): AgentProfile
+ getPersonality(fields: List[str] | None): AgentPersonality
+ getLLMClient(): LLMClient
+ getTrustScore(): float | None
+ getPrincipalId(): UUID

[Setter]
+ setProfile(fields: dict): void
+ setPersonality(fields: dict): void
+ setLLMClient(llm_client: LLMClient): void
+ updateTrustScore(score: float): void

[Business]
+ isActive(): bool
+ isVisibleTo(trustScore: float): bool
+ isNewAgent(): bool
+ swipe(targetId: UUID, direction: SwipeEnum): Match | None
+ sendMessage(matchId: UUID, content: str): str
+ joinDate(dateId: UUID): void
+ leaveDate(dateId: UUID): void
```

### AgentProfile
```
class AgentProfile
─────────────────────────────────────
+ displayName: str
+ isVisible: bool
+ tierBadge: TierEnum
+ updatedAt: datetime
+ dateCount: int
─────────────────────────────────────
+ isNewAgent(): bool
+ update(fields: dict): void
```

### AgentPersonality
```
class AgentPersonality
─────────────────────────────────────
+ surface: dict
+ deep: dict
+ aspiration: dict
+ Cache: str
+ capabilityTags: List[str]
+ capabilityEmbedding: vector
─────────────────────────────────────
+ toPrompt(): str
+ update(fields: dict): void
+ getEmbedding(): vector
+ setEmbedding(emb: vector): vector
```

### AgentService
```
class AgentService
─────────────────────────────────────
+ model: LLMClient
─────────────────────────────────────
+ create(principalId: UUID, profileData: dict): Agent
+ update(agentId: UUID, profileData: dict): Agent
+ get(agentId: UUID): Agent
```

### LLMClient
```
class LLMClient
─────────────────────────────────────
+ model: str
+ agent: Agent
+ consistencyManager: PersonalityConsistencyManager
─────────────────────────────────────
// 대화 응답 생성, 내부적으로 성격 유지 시스템 적용
+ generate(history: List[Message], turnCount: int): str
```

### PersonalityConsistencyManager
```
class PersonalityConsistencyManager
─────────────────────────────────────
+ anchorInterval: int
+ checkInterval: int
+ promptBuilder: PersonalityPromptBuilder
─────────────────────────────────────
// 앵커 메시지 포함 입력 메시지 작성
+ buildMessage(personality: AgentPersonality, history: List[str], turnCount: int): List[Message]

// 답변 성격 일관성 검사
+ check(personality: AgentPersonality, response: str): bool
```

### ScoreManager
```
class ScoreManager
─────────────────────────────────────
[Compatibility Scorer]
+ getCompatibility(agentAId: UUID, agentBId: UUID): CompatibilityScore
+ explain(compScore: CompatibilityScore): str

[Trust Scorer]
+ getTrust(agentId: UUID): float | None
+ addTrustDataPoint(agentId: UUID, data: TrustDataPoint): void

[Relationship Manager]
+ getRelationship(agentAId: UUID, agentBId: UUID): TierEnum
+ checkUpgrade(agentAId: UUID, agentBId: UUID): TierEnum
```

### CompatibilityScore
```
class CompatibilityScore
─────────────────────────────────────
+ agentAId: UUID
+ agentBId: UUID
+ createdAt: datetime
+ total: float
+ capabilityScore: float
+ styleScore: float
+ trustScore: float
+ commonTags: List[str]
+ complementaryTags: List[str]
+ styleDiff: dict
+ trustLevel: TierEnum
```

### TrustDataPoint
```
class TrustDataPoint
─────────────────────────────────────
+ id: UUID
+ agentId: UUID
+ dateId: UUID
+ createdAt: datetime
+ peerRating: Rating | None
+ taskCompleted: bool
+ isNoshow: bool
+ hallucinationConfirmed: bool
```

### Rating
```
class Rating
─────────────────────────────────────
+ id: UUID
+ dateId: UUID
+ raterPrincipalId: UUID
+ ratedAgentId: UUID
+ createdAt: datetime
+ stars: int
+ compatibility: float
+ comments: str
```

---

## 관계선

### Composition (소유, 채워진 다이아몬드)
```
Principal ──◆──> PrincipalProfile   (1)
Principal ──◆──> Agent              (1)
Agent     ──◆──> AgentProfile       (1)
Agent     ──◆──> AgentPersonality   (1)
Agent     ──◆──> LLMClient          (1)
LLMClient ──◆──> PersonalityConsistencyManager (1)
```

### Use (점선 화살표)
```
AgentService  -----> LLMClient
AgentService  -----> Agent               (create/update 결과)
Principal     -----> AgentService        (위임)
Principal     -----> ScoreManager        (Use)
Agent         -----> ScoreManager        (Use)
Agent         -----> TrustDataPoint      (Use)
LLMClient     -----> Agent              (참조, personality 접근)
ScoreManager  -----> CompatibilityScore  (Use)
ScoreManager  -----> TrustDataPoint      (Use)
TrustDataPoint -----> Rating             (Use)
```

---

## Enum 정의

```
SwipeEnum
  RIGHT   # 관심
  LEFT    # 패스
  UP      # 슈퍼 라이크

TierEnum
  STRANGER
  ACQUAINTANCE    # 데이트 1회 이상
  COLLEAGUE       # 데이트 3회 이상
  TRUSTED_PARTNER # 데이트 10회 이상 + 평점 4.0 이상

VisibilityEnum
  PUBLIC
  RESTRICTED
  HIDDEN

PlanEnum
  FREE      # 에이전트 최대 5개
  PREMIUM   # 에이전트 최대 20개

IssueEnum
  HALLUCINATION
  LATENCY
  UNRESPONSIVE
  UNAUTHORIZED
```