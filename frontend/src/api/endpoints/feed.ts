import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, FeedResponse, SwipeRequest, SwipeResponse } from "../types";
import { MIGRATE } from "../migration-flags";
import { mapFeedResponse, mapSwipeRequest, mapSwipeResponse } from "../adapters";
import type { BeFeedResponse, BeSwipeResponse } from "../adapters";
import { matchKeys } from "./matches";

export const feedKeys = {
  all: ["feed"] as const,
  list: (agentId: AgentId) => ["feed", agentId] as const,
};

const PAGE_SIZE = 20;

export function useFeed(agentId: AgentId | undefined) {
  return useInfiniteQuery({
    queryKey: feedKeys.list(agentId ?? ""),
    queryFn: ({ pageParam }) =>
      MIGRATE.feed
        ? api
            .get<BeFeedResponse>(`/agents/${agentId}/feed`, {
              query: { cursor: pageParam, limit: PAGE_SIZE },
            })
            .then(mapFeedResponse)
        : api.get<FeedResponse>(`/feed/${agentId}`, {
            query: { cursor: pageParam, limit: PAGE_SIZE },
          }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
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
    onSuccess: (res) => {
      if (agentId) qc.invalidateQueries({ queryKey: feedKeys.list(agentId) });
      // 매치가 성사된 swipe라면 채팅 탭(useActiveMatches)도 즉시 새로고침해야 한다.
      if (res.matched) qc.invalidateQueries({ queryKey: matchKeys.all });
    },
  });
}
