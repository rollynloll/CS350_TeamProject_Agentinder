import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, AnalyticsResponse } from "../types";

export const analyticsKeys = {
  all: ["analytics"] as const,
  forAgent: (agentId: AgentId, period: string) => ["analytics", agentId, period] as const,
};

export function useAnalytics(
  agentId: AgentId | undefined,
  period: "7d" | "30d" | "90d" | "all" = "30d",
) {
  return useQuery({
    queryKey: analyticsKeys.forAgent(agentId ?? "", period),
    queryFn: () =>
      api.get<AnalyticsResponse>(`/agents/${agentId}/analytics`, { query: { period } }),
    enabled: Boolean(agentId),
  });
}
