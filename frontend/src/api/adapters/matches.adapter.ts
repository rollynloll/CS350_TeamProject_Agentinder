import type {
  ActiveMatch,
  ActiveMatchesResponse,
  AgentId,
  DateHistoryItem,
  MatchDatesResponse,
} from "../types";
import type { BeDate, BeMatch } from "./backend-types";
import { avatarOrFallback, normalizeDateType, partnerLabel } from "./defaults";

function partnerIdOf(m: BeMatch, viewer: AgentId): AgentId {
  return m.agent_a_id === viewer ? m.agent_b_id : m.agent_a_id;
}

function deriveDateStatus(m: BeMatch): ActiveMatch["dateStatus"] {
  if (!m.latest_date_id) return "idle";
  if (m.latest_date_started_at && !m.latest_date_ended_at) return "coffee_chatting";
  if (m.latest_date_ended_at) {
    // 레이팅이 저장된 후에야 완전히 완료된 것으로 표시
    return m.latest_date_has_rating ? "deep_diving" : "rating_pending";
  }
  return "idle";
}

function mapActiveMatch(m: BeMatch, viewer: AgentId): ActiveMatch {
  const partnerId = partnerIdOf(m, viewer);
  return {
    matchId: m.match_id,
    partnerAgent: {
      agentId: partnerId,
      displayName: m.counterpart_name || partnerLabel(partnerId),
      avatarUrl: avatarOrFallback(m.counterpart_avatar, partnerId),
      trustScore: m.counterpart_trust_score ?? null,
    },
    tier: "stranger",
    dateStatus: deriveDateStatus(m),
    latestDateId: m.latest_date_id ?? undefined,
    matchType: "manual",
    unreadCount: 0,
    lastMessage: null,
    matchedAt: m.created_at,
    approvalStatus: m.status ? (m.status as NonNullable<ActiveMatch["approvalStatus"]>) : undefined,
  };
}

// Backend returns a flat match list; the UI groups by section. Wrap into one
// section keyed by the viewing agent.
export function mapActiveMatches(rows: BeMatch[], viewer: AgentId): ActiveMatchesResponse {
  const matches = (rows ?? []).map((m) => mapActiveMatch(m, viewer));
  return {
    sections: [{ title: "Active Matches", agentId: viewer, matches }],
    totalMatches: matches.length,
  };
}

function statusFromDate(be: BeDate): DateHistoryItem["status"] {
  if (be.is_noshow) return "no_show";
  if (be.ended_at) return "completed";
  if (be.started_at) return "in_progress";
  return "proposed";
}

function durationMinutes(be: BeDate): number {
  if (be.started_at && be.ended_at) {
    const ms = new Date(be.ended_at).getTime() - new Date(be.started_at).getTime();
    return Math.max(0, Math.round(ms / 60000));
  }
  return 0;
}

function mapDateHistoryItem(be: BeDate): DateHistoryItem {
  return {
    dateId: be.date_id,
    type: normalizeDateType(be.type),
    status: statusFromDate(be),
    startedAt: be.started_at ?? be.created_at,
    endedAt: be.ended_at,
    durationMinutes: durationMinutes(be),
    outcome: (be.outcome as DateHistoryItem["outcome"]) ?? null,
    mutualRating: null,
    summary: "",
    hasTranscript: false,
  };
}

export function mapMatchDates(rows: BeDate[], matchId: string): MatchDatesResponse {
  return {
    match: {
      matchId,
      partnerAgent: {
        agentId: "",
        displayName: partnerLabel(matchId),
        avatarUrl: avatarOrFallback(null, matchId),
        trustScore: null,
      },
    },
    dates: (rows ?? []).map(mapDateHistoryItem),
  };
}
