import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, FeedResponse, SwipeRequest, SwipeResponse } from "../types";
import { MIGRATE } from "../migration-flags";
import { mapFeedResponse, mapSwipeRequest, mapSwipeResponse } from "../adapters";
import type { BeFeedResponse, BeSwipeResponse } from "../adapters";

export const feedKeys = {
  all: ["feed"] as const,
  list: (agentId: AgentId, cursor?: string) => ["feed", agentId, cursor] as const,
};

export function useFeed(agentId: AgentId | undefined, cursor?: string) {
  return useQuery({
    queryKey: feedKeys.list(agentId ?? "", cursor),
    queryFn: () =>
      MIGRATE.feed
        ? api
            .get<BeFeedResponse>(`/agents/${agentId}/feed`, { query: { cursor, limit: 20 } })
            .then(mapFeedResponse)
        : api.get<FeedResponse>(`/feed/${agentId}`, { query: { cursor, limit: 20 } }),
    enabled: Boolean(agentId),
  });
}

export function useSwipe(agentId: AgentId | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SwipeRequest) =>
      MIGRATE.swipe
        ? api
            .post<BeSwipeResponse>(`/agents/${agentId}/swipe`, mapSwipeRequest(body))
            .then(mapSwipeResponse)
        : api.post<SwipeResponse, SwipeRequest>(`/feed/${agentId}/swipe`, body),
    onSuccess: () => {
      if (agentId) qc.invalidateQueries({ queryKey: feedKeys.list(agentId) });
    },
  });
}
