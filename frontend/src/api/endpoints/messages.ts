import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { ConversationResponse, MatchId } from "../types";

export const messageKeys = {
  all: ["messages"] as const,
  conversation: (matchId: MatchId) => ["messages", matchId] as const,
};

export function useConversation(matchId: MatchId | undefined) {
  return useQuery({
    queryKey: messageKeys.conversation(matchId ?? ""),
    queryFn: () => api.get<ConversationResponse>(`/matches/${matchId}/messages`),
    enabled: Boolean(matchId),
  });
}
