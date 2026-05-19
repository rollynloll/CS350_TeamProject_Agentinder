import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, FeedResponse, SwipeRequest, SwipeResponse } from "../types";

export const feedKeys = {
  all: ["feed"] as const,
  list: (agentId: AgentId, cursor?: string) => ["feed", agentId, cursor] as const,
};

export function useFeed(agentId: AgentId | undefined, cursor?: string) {
  return useQuery({
    queryKey: feedKeys.list(agentId ?? "", cursor),
    queryFn: () =>
      api.get<FeedResponse>(`/feed/${agentId}`, { query: { cursor, limit: 20 } }),
    enabled: Boolean(agentId),
  });
}

export function useSwipe(agentId: AgentId | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SwipeRequest) =>
      api.post<SwipeResponse, SwipeRequest>(`/feed/${agentId}/swipe`, body),
    onSuccess: () => {
      if (agentId) qc.invalidateQueries({ queryKey: feedKeys.list(agentId) });
    },
  });
}
