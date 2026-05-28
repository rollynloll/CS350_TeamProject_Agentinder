import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { ActiveMatchesResponse, AgentId } from "../types";

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
      api.get<ActiveMatchesResponse>(`/agents/${agentId}/matches`, { query: { status } }),
    enabled: Boolean(agentId),
  });
}
