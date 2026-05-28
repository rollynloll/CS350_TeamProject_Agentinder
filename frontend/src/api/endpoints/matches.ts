import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { ActiveMatchesResponse, AgentId } from "../types";
import { MIGRATE } from "../migration-flags";
import { mapActiveMatches } from "../adapters";
import type { BeMatch } from "../adapters";

export const matchKeys = {
  all: ["matches"] as const,
  active: (agentId: AgentId, status: string) => ["matches", agentId, status] as const,
};

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
