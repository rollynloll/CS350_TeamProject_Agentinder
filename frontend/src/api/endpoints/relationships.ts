import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, MatchDatesResponse, MatchId, RelationshipsResponse, Tier } from "../types";

export const relationshipKeys = {
  all: ["relationships"] as const,
  forAgent: (agentId: AgentId, tier?: Tier) => ["relationships", agentId, tier] as const,
  matchDates: (matchId: MatchId) => ["relationships", "match", matchId, "dates"] as const,
};

export function useRelationships(agentId: AgentId | undefined, tier?: Tier) {
  return useQuery({
    queryKey: relationshipKeys.forAgent(agentId ?? "", tier),
    queryFn: () =>
      api.get<RelationshipsResponse>(`/agents/${agentId}/relationships`, { query: { tier } }),
    enabled: Boolean(agentId),
  });
}

export function useMatchDates(matchId: MatchId | undefined) {
  return useQuery({
    queryKey: relationshipKeys.matchDates(matchId ?? ""),
    queryFn: () => api.get<MatchDatesResponse>(`/matches/${matchId}/dates`),
    enabled: Boolean(matchId),
  });
}
