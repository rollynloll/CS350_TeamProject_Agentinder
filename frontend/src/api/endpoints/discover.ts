import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, DiscoverFilters, DiscoverResponse } from "../types";

export const discoverKeys = {
  all: ["discover"] as const,
  search: (agentId: AgentId, filters: DiscoverFilters) =>
    ["discover", agentId, filters] as const,
};

export function useDiscover(agentId: AgentId | undefined, filters: DiscoverFilters = {}) {
  return useQuery({
    queryKey: discoverKeys.search(agentId ?? "", filters),
    queryFn: () =>
      api.get<DiscoverResponse>(`/discover/${agentId}`, {
        query: {
          q: filters.q,
          capability: filters.capability,
          trustMin: filters.trustMin,
          trustMax: filters.trustMax,
          style: filters.style,
          domain: filters.domain,
          availability: filters.availability,
          limit: 24,
        },
      }),
    enabled: Boolean(agentId),
  });
}
