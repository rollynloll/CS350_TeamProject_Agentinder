// Raw response shapes as returned by the FastAPI backend (snake_case).
// These are unwrapped from the `{data, meta, error}` envelope by `apiFetch`,
// so each type below describes the `data` payload only.

export type BeAgentListItem = {
  agent_id: string;
  display_name: string;
  visibility: string;
  tier_badge: string;
  avatar_url: string | null;
  created_at: string;
};

export type BeAgentProfile = {
  agent_id: string;
  principal_id: string;
  display_name: string;
  visibility: string;
  trust_score: number | null;
  tier_badge: string;
  date_count: number;
  avatar_url: string | null;
  has_embedding: boolean;
  // get_agent_row 확장 필드 (agent_profiles + agent_personalities)
  bio?: string;
  style_formal?: number; // 0~100
  style_verbose?: number; // 0~100
  style_bold?: number; // 0~100
  capability_tags?: string[];
  available_timezones?: string[];
  llm_model?: string;
};

export type BeCreateAgentResponse = {
  agent_id: string;
  principal_id: string;
  api_key: string;
  display_name: string;
  visibility: string;
  tier_badge: string;
};

export type BeUpdateAgentResponse = {
  agent_id: string;
  display_name: string;
  visibility: string;
  tier_badge: string;
};

export type BeCreateAgentRequest = {
  display_name: string;
  visibility?: string;
  capability_tags?: string[];
  available_timezones?: string[];
  personality?: Record<string, unknown>;
  llm_model?: string;
  avatar?: string;
};

export type BeUpdateAgentRequest = {
  display_name?: string;
  visibility?: string;
  capability_tags?: string[];
  available_timezones?: string[];
  personality?: Record<string, unknown>;
  llm_model?: string;
  avatar?: string;
};

export type BeFeedItem = {
  agent_id: string;
  display_name: string;
  avatar_url: string | null;
  tier_badge: string;
  trust_score: number | null;
  compatibility_total: number;
  common_tags: string[];
};

export type BeFeedResponse = { items: BeFeedItem[]; next_cursor: string | null };

// Discover endpoint reuses the feed card shape; backend also echoes the
// resolved filters under `applied_filters` (snake_case).
export type BeDiscoverResponse = {
  items: BeFeedItem[];
  next_cursor: string | null;
  applied_filters?: Record<string, unknown>;
};

export type BeSwipeRequest = { target_id: string; direction: "right" | "left" | "up" };

export type BeSwipeResponse = { swiped: boolean; match: { match_id: string } | null };

export type BeMatch = {
  match_id: string;
  agent_a_id: string;
  agent_b_id: string;
  status: string | null;
  created_at: string;
};

export type BeMessage = {
  message_id: string;
  match_id: string;
  sender_agent_id: string;
  content: string;
  is_read: boolean;
  created_at: string;
};

export type BeMessagesResponse = { items: BeMessage[]; next_cursor: string | null };

export type BeDate = {
  date_id: string;
  match_id: string;
  type: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  ended_at: string | null;
  outcome: string | null;
  is_noshow: boolean;
  created_at: string;
};

export type BeEndDateRequest = {
  outcome?: string;
  rating_stars?: number;
  rating_compatibility?: number;
  rated_agent_id?: string;
};

export type BeEndDateResponse = { date_id: string; outcome: string | null };
