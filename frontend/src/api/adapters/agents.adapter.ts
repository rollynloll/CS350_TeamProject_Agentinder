import type {
  AgentCreateRequest,
  AgentListItem,
  AgentListResponse,
  AgentProfile,
  AgentUpdateRequest,
} from "../types";
import type {
  BeAgentListItem,
  BeAgentProfile,
  BeCreateAgentRequest,
  BeCreateAgentResponse,
  BeUpdateAgentRequest,
  BeUpdateAgentResponse,
} from "./backend-types";
import {
  DEFAULT_INTERACTION_STYLE,
  avatarOrFallback,
  normalizeVisibility,
  nowIso,
  trustBadgeFrom,
} from "./defaults";

function mapAgentListItem(be: BeAgentListItem): AgentListItem {
  return {
    agentId: be.agent_id,
    displayName: be.display_name,
    avatarUrl: avatarOrFallback(be.avatar_url, be.agent_id),
    bioSnippet: "",
    trustScore: null,
    trustBadge: trustBadgeFrom(be.tier_badge),
    activeMatchCount: 0,
    profileCompleteness: 0,
    createdAt: be.created_at,
  };
}

export function mapAgentList(be: BeAgentListItem[]): AgentListResponse {
  return { agents: (be ?? []).map(mapAgentListItem) };
}

// The backend GET /v1/agents/{id} returns a minimal row — bio, capabilityTags,
// availability and portfolio live in other tables not exposed by this route, so
// we synthesize empty values. `base` lets callers merge cached values in.
export function mapAgentProfile(be: BeAgentProfile, base?: Partial<AgentProfile>): AgentProfile {
  return {
    agentId: be.agent_id,
    displayName: be.display_name,
    avatarUrl: avatarOrFallback(be.avatar_url, be.agent_id),
    bio: base?.bio ?? "",
    capabilityTags: base?.capabilityTags ?? [],
    interactionStyle: base?.interactionStyle ?? DEFAULT_INTERACTION_STYLE,
    availability: base?.availability ?? { timezone: "UTC", windows: [] },
    portfolio: base?.portfolio ?? [],
    trustScore: be.trust_score,
    trustBadge: trustBadgeFrom(be.tier_badge),
    visibility: normalizeVisibility(be.visibility),
    createdAt: base?.createdAt ?? nowIso(),
    updatedAt: nowIso(),
  };
}

export function mapCreateRequest(req: AgentCreateRequest): BeCreateAgentRequest {
  return {
    display_name: req.displayName,
    visibility: "PUBLIC",
    capability_tags: req.capabilityTags ?? [],
    available_timezones: req.availability?.timezone ? [req.availability.timezone] : [],
    personality: { surface: { bio: req.bio }, interaction_style: req.interactionStyle },
    llm_model: "gpt-4o",
    avatar: "",
  };
}

// Create returns a thin payload (no full profile) — produce an AgentProfile shell.
export function mapCreateResponse(be: BeCreateAgentResponse, req?: AgentCreateRequest): AgentProfile {
  return {
    agentId: be.agent_id,
    displayName: be.display_name,
    avatarUrl: avatarOrFallback(null, be.agent_id),
    bio: req?.bio ?? "",
    capabilityTags: req?.capabilityTags ?? [],
    interactionStyle: req?.interactionStyle ?? DEFAULT_INTERACTION_STYLE,
    availability: req?.availability ?? { timezone: "UTC", windows: [] },
    portfolio: [],
    trustScore: null,
    trustBadge: trustBadgeFrom(be.tier_badge),
    visibility: normalizeVisibility(be.visibility),
    createdAt: nowIso(),
    updatedAt: nowIso(),
    apiKeyMasked: be.api_key,
  };
}

export function mapUpdateRequest(req: AgentUpdateRequest): BeUpdateAgentRequest {
  const out: BeUpdateAgentRequest = {};
  if (req.displayName !== undefined) out.display_name = req.displayName;
  if (req.visibility !== undefined) out.visibility = req.visibility.toUpperCase();
  if (req.capabilityTags !== undefined) out.capability_tags = req.capabilityTags;
  if (req.availability?.timezone) out.available_timezones = [req.availability.timezone];
  if (req.bio !== undefined || req.interactionStyle !== undefined) {
    out.personality = { surface: { bio: req.bio }, interaction_style: req.interactionStyle };
  }
  return out;
}

export function mapUpdateResponse(be: BeUpdateAgentResponse, base?: Partial<AgentProfile>): AgentProfile {
  return {
    agentId: be.agent_id,
    displayName: be.display_name,
    avatarUrl: base?.avatarUrl ?? avatarOrFallback(null, be.agent_id),
    bio: base?.bio ?? "",
    capabilityTags: base?.capabilityTags ?? [],
    interactionStyle: base?.interactionStyle ?? DEFAULT_INTERACTION_STYLE,
    availability: base?.availability ?? { timezone: "UTC", windows: [] },
    portfolio: base?.portfolio ?? [],
    trustScore: base?.trustScore ?? null,
    trustBadge: trustBadgeFrom(be.tier_badge),
    visibility: normalizeVisibility(be.visibility),
    createdAt: base?.createdAt ?? nowIso(),
    updatedAt: nowIso(),
  };
}
