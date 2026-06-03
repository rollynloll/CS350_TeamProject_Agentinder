import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, DiscoverFilters, DiscoverResponse } from "../types";
import { MIGRATE } from "../migration-flags";
import { mapDiscoverResponse } from "../adapters";
import type { BeDiscoverResponse } from "../adapters";

export const discoverKeys = {
  all: ["discover"] as const,
  search: (agentId: AgentId, filters: DiscoverFilters) =>
    ["discover", agentId, filters] as const,
};

export function useDiscover(agentId: AgentId | undefined, filters: DiscoverFilters = {}) {
  return useQuery({
    queryKey: discoverKeys.search(agentId ?? "", filters),
    queryFn: () =>
      MIGRATE.discover
        ? api
            .get<BeDiscoverResponse>(`/agents/${agentId}/discover`, {
              query: {
                q: filters.q,
                // Backend accepts a comma-separated capability tag list.
                capability: filters.capability?.join(","),
                trustMin: filters.trustMin,
                trustMax: filters.trustMax,
                style: filters.style,
                domain: filters.domain,
                availability: filters.availability,
                limit: 24,
              },
            })
            .then(mapDiscoverResponse)
        : api.get<DiscoverResponse>(`/discover/${agentId}`, {
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
