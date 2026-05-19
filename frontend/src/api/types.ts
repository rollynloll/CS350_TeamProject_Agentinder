// Types mirror docs/Agentinder_API_Specification_v2.docx §3.
// Keep field names in camelCase as documented.

export type Envelope<T> = {
  data: T | null;
  meta?: {
    requestId?: string;
    timestamp?: string;
    pagination?: Pagination;
  };
  error: ApiError | null;
};

export type Pagination = {
  nextCursor: string | null;
  hasMore: boolean;
  totalCount?: number;
};

export type ApiError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

// ---- shared domain primitives ----

export type AgentId = string;
export type MatchId = string;
export type DateId = string;
export type MessageId = string;

export type Tier = "stranger" | "acquaintance" | "colleague" | "trusted_partner";
export type Visibility = "public" | "restricted" | "hidden";
export type SwipeAction = "like" | "pass" | "super_like";
export type DateType = "coffee_chat" | "activity_date" | "deep_dive";
export type DateStatus = "proposed" | "in_progress" | "completed" | "cancelled" | "no_show";

export type InteractionStyle = {
  verbosity?: "verbose" | "concise";
  formality?: "formal" | "casual";
  cautiousness?: "cautious" | "bold";
  boldness?: "cautious" | "moderate" | "bold";
};

export type AvailabilityWindow = {
  day: "MON" | "TUE" | "WED" | "THU" | "FRI" | "SAT" | "SUN";
  start: string; // HH:mm
  end: string;
};

export type FeedCard = {
  agentId: AgentId;
  displayName: string;
  avatarUrl: string;
  bioSnippet: string;
  topTags: string[];
  compatibilityScore: number; // 0–1
  trustScore: number | null; // null = new agent
  trustBadge: "new_agent" | "verified" | string;
  interactionStyle: InteractionStyle;
  availabilityStatus: "available" | "busy" | "offline";
  /** Mock-only callout for Feed Main00 — pending API spec update with Team A. */
  superLikedYou?: boolean;
};

export type PartnerAgent = {
  agentId: AgentId;
  displayName: string;
  avatarUrl: string;
  trustScore?: number | null;
};

// ---- §3.1 Feed ----

export type FeedResponse = { cards: FeedCard[] };

export type SwipeRequest = {
  targetAgentId: AgentId;
  action: SwipeAction;
};

export type SwipeResponse = {
  matched: boolean;
  matchId: MatchId | null;
  icebreakers: string[] | null;
};

// ---- §3.2 Discover ----

export type DiscoverFilters = {
  q?: string;
  capability?: string[];
  trustMin?: number;
  trustMax?: number;
  style?: string;
  domain?: string;
  availability?: string;
};

export type DiscoverResponse = {
  cards: FeedCard[];
  appliedFilters: Partial<DiscoverFilters>;
  totalResults: number;
};

// ---- §3.3 My Profiles ----

export type AgentListItem = {
  agentId: AgentId;
  displayName: string;
  avatarUrl: string;
  bioSnippet: string;
  trustScore: number | null;
  trustBadge: string;
  activeMatchCount: number;
  profileCompleteness: number; // 0–1
  createdAt: string;
  /** Mock-only — pending API spec extension. */
  summary?: string;
  /** Mock-only — pending API spec extension. */
  capabilityTags?: string[];
  /** Mock-only — pending API spec extension. */
  dateStatus?: "coffee_chatting" | "deep_diving" | "idle";
};

export type AgentListResponse = { agents: AgentListItem[] };

// ---- §3.4 Profile Detail ----

export type AgentProfile = {
  agentId: AgentId;
  displayName: string;
  avatarUrl: string;
  bio: string;
  capabilityTags: string[];
  interactionStyle: InteractionStyle;
  availability: { timezone: string; windows: AvailabilityWindow[] };
  portfolio: Array<{
    dateId: DateId;
    title: string;
    outcome: "successful" | "neutral" | "unsuccessful";
    rating: number;
  }>;
  trustScore: number | null;
  trustBadge: string;
  visibility: Visibility;
  createdAt: string;
  updatedAt: string;
  /** Mock-only — pending API spec extension. */
  baseModel?: string;
  /** Mock-only — pending API spec extension. */
  apiKeyMasked?: string;
  /** Mock-only — 0–100 sliders. */
  styleCasual?: number;
  /** Mock-only — 0–100 sliders. */
  styleDetail?: number;
  /** Mock-only — 0–100 sliders. */
  styleBold?: number;
};

export type AgentCreateRequest = {
  displayName: string;
  bio: string;
  capabilityTags: string[];
  interactionStyle: InteractionStyle;
  availability: AgentProfile["availability"];
};

export type AgentUpdateRequest = Partial<
  Omit<AgentProfile, "agentId" | "trustScore" | "trustBadge" | "createdAt" | "updatedAt" | "portfolio">
>;

// ---- §3.6 Analytics ----

export type AnalyticsResponse = {
  trustScoreTrend: Array<{ date: string; score: number }>;
  dateStats: {
    totalDates: number;
    successRate: number;
    byType: Record<DateType, { count: number; successRate: number }>;
  };
  compatibilityBreakdown: {
    topDomains: Array<{ domain: string; avgScore: number }>;
    styleMatchRate: number;
  };
  relationshipGrowth: Array<{
    date: string;
    stranger: number;
    acquaintance: number;
    colleague: number;
    trusted_partner: number;
  }>;
  relationshipSummary: {
    totalRelationships: number;
    byTier: Record<Tier, number>;
    recentActivity: Array<{
      matchId: MatchId;
      partnerDisplayName: string;
      partnerAvatarUrl: string;
      tier: Tier;
      lastInteractionAt: string;
      mutualRating: number;
    }>;
  };
};

// ---- §3.7 Active Matches ----

export type ActiveMatch = {
  matchId: MatchId;
  partnerAgent: PartnerAgent;
  tier: Tier;
  dateStatus: "coffee_chatting" | "deep_diving" | "idle";
  unreadCount: number;
  lastMessage: {
    preview: string;
    sentAt: string;
    isFromMe: boolean;
  } | null;
  matchedAt: string;
  /** Mock-only — pending API spec extension. */
  compatibilityScore?: number;
};

export type ActiveMatchesResponse = {
  sections: Array<{
    title: string;
    agentId: AgentId;
    matches: ActiveMatch[];
  }>;
  totalMatches: number;
};

// ---- §3.8 Relationships / Match History ----

export type RelationshipItem = {
  matchId: MatchId;
  partnerAgent: PartnerAgent;
  tier: Tier;
  totalDates: number;
  lastDateAt: string;
  mutualRating: number;
  lastDateSummary: string;
};

export type RelationshipsResponse = {
  groups: Array<{
    tier: Tier;
    count: number;
    relationships: RelationshipItem[];
  }>;
  totalRelationships: number;
};

export type DateHistoryItem = {
  dateId: DateId;
  type: DateType;
  status: DateStatus;
  startedAt: string;
  endedAt: string | null;
  durationMinutes: number;
  outcome: "successful" | "neutral" | "unsuccessful" | null;
  mutualRating: number | null;
  summary: string;
  hasTranscript: boolean;
};

export type MatchDatesResponse = {
  match: { matchId: MatchId; partnerAgent: PartnerAgent };
  dates: DateHistoryItem[];
};

// ---- §3.9 Live Date ----

export type LiveDateResponse = {
  dateId: DateId;
  type: DateType;
  status: DateStatus;
  partnerAgent: PartnerAgent;
  startedAt: string;
  maxDurationMinutes: number;
  elapsedMinutes: number;
  icebreakers: string[];
  recentMessages: Array<{
    messageId: MessageId;
    senderId: AgentId;
    content: string;
    sentAt: string;
  }>;
};

export type ScheduleDateRequest = {
  type: DateType;
  proposedTime: string;
  message?: string;
};

export type ScheduleDateResponse = {
  dateId: DateId;
  status: DateStatus;
  type: DateType;
  proposedTime: string;
};

export type EndDateRequest = {
  action: "end";
  outcome: "successful" | "neutral" | "unsuccessful";
  rating: number;
  feedback?: string;
};

// ---- §3.10 Conversation ----

export type ChatMessage = {
  messageId: MessageId;
  senderId: AgentId;
  type: "text" | "json" | "file";
  content: string;
  sentAt: string;
  readAt?: string | null;
};

export type ConversationResponse = {
  matchInfo: {
    matchId: MatchId;
    partnerAgent: PartnerAgent;
    tier: Tier;
    canScheduleDate: boolean;
    canSendMultimedia: boolean;
  };
  messages: ChatMessage[];
};

// ---- §3.11 Settings ----

export type SettingsResponse = {
  account: { email: string; displayName: string; createdAt: string };
  apiKeys: Array<{
    keyId: string;
    name: string;
    lastUsedAt: string | null;
    createdAt: string;
  }>;
  notifications: {
    matchAlerts: boolean;
    dateReminders: boolean;
    weeklyDigest: boolean;
    messagePreview: boolean;
  };
  preferences: {
    globalTrustThreshold: number;
    autoMatchRules: {
      enabled: boolean;
      minCompatibility: number;
      minTrust: number;
    };
  };
  privacy: {
    profileVisibility: Visibility;
    dateTranscriptSharing: "mutual_consent" | "owner_only" | "platform";
    analyticsOptIn: boolean;
  };
};

export type SettingsPatch = {
  notifications?: Partial<SettingsResponse["notifications"]>;
  preferences?: Partial<SettingsResponse["preferences"]>;
  privacy?: Partial<SettingsResponse["privacy"]>;
};

// ---- WebSocket frame (spec §4.2) ----

export type WsFrame<P = unknown> = {
  type: "subscribe" | "unsubscribe" | "event" | "action" | "ack";
  topic: string;
  payload?: P;
  id: string;
  timestamp: string;
};
