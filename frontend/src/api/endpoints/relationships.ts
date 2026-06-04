import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, MatchDatesResponse, MatchId, RelationshipsResponse, Tier } from "../types";
import { MIGRATE } from "../migration-flags";
import { mapMatchDates } from "../adapters";
import type { BeDate } from "../adapters";

export const relationshipKeys = {
  all: ["relationships"] as const,
  forAgent: (agentId: AgentId, tier?: Tier) => ["relationships", agentId, tier] as const,
  matchDates: (matchId: MatchId) => ["relationships", "match", matchId, "dates"] as const,
};

// 백엔드 GET /v1/agents/{agentId}/relationships 응답 타입
type BeRelGroup = {
  tier: string;
  count: number;
  relationships: Array<{
    partnerId: string;
    matchId: string | null;
    partnerName: string;
    partnerAvatar: string;
    partnerTrustScore: number | null;
    tier: string;
    successfulDates: number;
    avgRating: number | null;
    updatedAt: string | null;
  }>;
};
type BeRelResponse = { groups: BeRelGroup[]; totalRelationships: number };

function mapBeRelationships(be: BeRelResponse): RelationshipsResponse {
  return {
    groups: be.groups.map((g) => ({
      tier: g.tier as Tier,
      count: g.count,
      relationships: g.relationships.map((r) => ({
        matchId: r.matchId ?? r.partnerId,
        partnerAgent: {
          agentId: r.partnerId,
          displayName: r.partnerName,
          avatarUrl: r.partnerAvatar,
          trustScore: r.partnerTrustScore,
        },
        tier: r.tier as Tier,
        totalDates: r.successfulDates,
        lastDateAt: r.updatedAt ?? new Date().toISOString(),
        mutualRating: r.avgRating ? r.avgRating * 5 : 0,
        lastDateSummary: "",
      })),
    })),
    totalRelationships: be.totalRelationships,
  };
}

export function useRelationships(agentId: AgentId | undefined, tier?: Tier) {
  return useQuery({
    queryKey: relationshipKeys.forAgent(agentId ?? "", tier),
    queryFn: () =>
      MIGRATE.relationships
        ? api
            .get<BeRelResponse>(`/agents/${agentId}/relationships`, { query: { tier } })
            .then(mapBeRelationships)
        : api.get<RelationshipsResponse>(`/agents/${agentId}/relationships`, { query: { tier } }),
    enabled: Boolean(agentId),
  });
}

export function useMatchDates(matchId: MatchId | undefined) {
  return useQuery({
    queryKey: relationshipKeys.matchDates(matchId ?? ""),
    queryFn: () =>
      MIGRATE.dateHistory
        ? api
            .get<BeDate[]>(`/matches/${matchId}/dates`)
            .then((rows) => mapMatchDates(rows, matchId ?? ""))
        : api.get<MatchDatesResponse>(`/matches/${matchId}/dates`),
    enabled: Boolean(matchId),
  });
}
