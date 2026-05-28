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

function mapActiveMatch(m: BeMatch, viewer: AgentId): ActiveMatch {
  const partnerId = partnerIdOf(m, viewer);
  return {
    matchId: m.match_id,
    partnerAgent: {
      agentId: partnerId,
      displayName: partnerLabel(partnerId),
      avatarUrl: avatarOrFallback(null, partnerId),
      trustScore: null,
    },
    tier: "stranger",
    dateStatus: "idle",
    unreadCount: 0,
    lastMessage: null,
    matchedAt: m.created_at,
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
