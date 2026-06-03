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
    queryFn: () =>
      MIGRATE.dateHistory
        ? api
            .get<BeDate[]>(`/matches/${matchId}/dates`)
            .then((rows) => mapMatchDates(rows, matchId ?? ""))
        : api.get<MatchDatesResponse>(`/matches/${matchId}/dates`),
    enabled: Boolean(matchId),
  });
}
