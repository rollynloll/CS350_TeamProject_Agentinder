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

// 백엔드 GET /v1/agents/{id}(get_agent_row)는 bio·style·capability_tags·available_timezones
// 를 함께 반환한다. portfolio 등 미노출 필드는 base(캐시) 또는 빈 값으로 채운다.
export function mapAgentProfile(be: BeAgentProfile, base?: Partial<AgentProfile>): AgentProfile {
  return {
    agentId: be.agent_id,
    displayName: be.display_name,
    avatarUrl: avatarOrFallback(be.avatar_url, be.agent_id),
    bio: be.bio ?? base?.bio ?? "",
    capabilityTags: be.capability_tags ?? base?.capabilityTags ?? [],
    interactionStyle: base?.interactionStyle ?? DEFAULT_INTERACTION_STYLE,
    // 백엔드 style_formal/verbose/bold(0~100) → 슬라이더(0~100) 1:1
    styleCasual: be.style_formal ?? base?.styleCasual,
    styleDetail: be.style_verbose ?? base?.styleDetail,
    styleBold: be.style_bold ?? base?.styleBold,
    availability:
      be.available_timezones && be.available_timezones.length > 0
        ? { timezone: be.available_timezones[0], windows: base?.availability?.windows ?? [] }
        : (base?.availability ?? { timezone: "UTC", windows: [] }),
    baseModel: be.llm_model ?? base?.baseModel,
    portfolio: base?.portfolio ?? [],
    trustScore: be.trust_score,
    trustBadge: trustBadgeFrom(be.tier_badge),
    visibility: normalizeVisibility(be.visibility),
    createdAt: base?.createdAt ?? nowIso(),
    updatedAt: nowIso(),
    autoMatch: be.auto_match ?? base?.autoMatch ?? false,
    taskDescription: be.task_description ?? base?.taskDescription ?? "",
  };
}

// 프론트 슬라이더(0~100) → 백엔드 surface.style_sliders(0.0~1.0).
// Casual→formal, Detail→verbose, Bold→bold (1:1).
function styleSlidersFrom(req: {
  styleCasual?: number;
  styleDetail?: number;
  styleBold?: number;
}): Record<string, number> {
  const s: Record<string, number> = {};
  if (req.styleCasual !== undefined) s.formal = req.styleCasual / 100;
  if (req.styleDetail !== undefined) s.verbose = req.styleDetail / 100;
  if (req.styleBold !== undefined) s.bold = req.styleBold / 100;
  return s;
}

export function mapCreateRequest(req: AgentCreateRequest): BeCreateAgentRequest {
  return {
    display_name: req.displayName,
    visibility: "PUBLIC",
    capability_tags: req.capabilityTags ?? [],
    available_timezones: req.availability?.timezone ? [req.availability.timezone] : [],
    personality: { surface: { bio: req.bio, style_sliders: styleSlidersFrom(req) } },
    llm_model: "gpt-4o",
    avatar: "",
    auto_match: req.autoMatch ?? false,
    task_description: req.taskDescription ?? "",
  };
}

// Create returns a thin payload (no full profile) — produce an AgentProfile shell.
export function mapCreateResponse(
  be: BeCreateAgentResponse,
  req?: AgentCreateRequest,
): AgentProfile {
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
    autoMatch: req?.autoMatch ?? false,
    taskDescription: req?.taskDescription ?? "",
  };
}

export function mapUpdateRequest(req: AgentUpdateRequest): BeUpdateAgentRequest {
  const out: BeUpdateAgentRequest = {};
  if (req.displayName !== undefined) out.display_name = req.displayName;
  if (req.visibility !== undefined) out.visibility = req.visibility.toUpperCase();
  if (req.capabilityTags !== undefined) out.capability_tags = req.capabilityTags;
  if (req.availability?.timezone) out.available_timezones = [req.availability.timezone];
  const hasStyle =
    req.styleCasual !== undefined || req.styleDetail !== undefined || req.styleBold !== undefined;
  if (req.bio !== undefined || hasStyle) {
    out.personality = { surface: { bio: req.bio ?? "", style_sliders: styleSlidersFrom(req) } };
  }
  if (req.autoMatch !== undefined) out.auto_match = req.autoMatch;
  if (req.taskDescription !== undefined) out.task_description = req.taskDescription;
  return out;
}

export function mapUpdateResponse(
  be: BeUpdateAgentResponse,
  base?: Partial<AgentProfile>,
): AgentProfile {
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
