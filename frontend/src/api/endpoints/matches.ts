import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { ActiveMatchesResponse, AgentId, MatchId } from "../types";
import { MIGRATE } from "../migration-flags";
import { mapActiveMatches } from "../adapters";
import type { BeMatch } from "../adapters";

export const matchKeys = {
  all: ["matches"] as const,
  active: (agentId: AgentId, status: string) => ["matches", agentId, status] as const,
};

type DecisionResponse = { match_id: string; status: string };

// SRS REQ-0205 / UC-0202: principal approves or rejects a pending match.
// Backend: POST /v1/matches/{id}/approve | /reject (no mock handler — real only).
export function useApproveMatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (matchId: MatchId) =>
      api.post<DecisionResponse>(`/matches/${matchId}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: matchKeys.all }),
  });
}

export function useRejectMatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (matchId: MatchId) =>
      api.post<DecisionResponse>(`/matches/${matchId}/reject`),
    onSuccess: () => qc.invalidateQueries({ queryKey: matchKeys.all }),
  });
}

export function useActiveMatches(
  agentId: AgentId | undefined,
  status: "active" | "archived" | "all" = "active",
) {
  return useQuery({
    queryKey: matchKeys.active(agentId ?? "", status),
    queryFn: () =>
      MIGRATE.matches
        ? api
            // Frontend status values don't map to the backend match_status_enum;
            // omit the filter and return all matches for the agent.
            .get<BeMatch[]>(`/matches`, { query: { agent_id: agentId } })
            .then((rows) => mapActiveMatches(rows, agentId ?? ""))
        : api.get<ActiveMatchesResponse>(`/agents/${agentId}/matches`, { query: { status } }),
    enabled: Boolean(agentId),
  });
}
