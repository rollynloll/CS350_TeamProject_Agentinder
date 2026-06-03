import type { FeedCard, FeedResponse, SwipeRequest, SwipeResponse } from "../types";
import type { BeFeedItem, BeFeedResponse, BeSwipeRequest, BeSwipeResponse } from "./backend-types";
import { DEFAULT_INTERACTION_STYLE, avatarOrFallback, trustBadgeFrom } from "./defaults";

export function mapFeedCard(be: BeFeedItem): FeedCard {
  return {
    agentId: be.agent_id,
    displayName: be.display_name,
    avatarUrl: avatarOrFallback(be.avatar_url, be.agent_id),
    bioSnippet: "",
    topTags: be.common_tags ?? [],
    compatibilityScore: be.compatibility_total,
    trustScore: be.trust_score,
    trustBadge: trustBadgeFrom(be.tier_badge),
    interactionStyle: DEFAULT_INTERACTION_STYLE,
    availabilityStatus: "available",
  };
}

export function mapFeedResponse(be: BeFeedResponse): FeedResponse {
  return {
    cards: (be.items ?? []).map(mapFeedCard),
    nextCursor: be.next_cursor ?? null,
  };
}

const ACTION_TO_DIRECTION: Record<SwipeRequest["action"], BeSwipeRequest["direction"]> = {
  like: "right",
  pass: "left",
  super_like: "up",
};

export function mapSwipeRequest(req: SwipeRequest): BeSwipeRequest {
  return { target_id: req.targetAgentId, direction: ACTION_TO_DIRECTION[req.action] };
}

export function mapSwipeResponse(be: BeSwipeResponse): SwipeResponse {
  return {
    matched: be.match != null,
    matchId: be.match?.match_id ?? null,
    icebreakers: null,
  };
}
