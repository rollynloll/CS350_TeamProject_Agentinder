import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { ConversationResponse, MatchId } from "../types";
import { MIGRATE } from "../migration-flags";
import { mapConversation } from "../adapters";
import type { BeMessagesResponse } from "../adapters";

export const messageKeys = {
  all: ["messages"] as const,
  conversation: (matchId: MatchId) => ["messages", matchId] as const,
};

export function useConversation(matchId: MatchId | undefined) {
  return useQuery({
    queryKey: messageKeys.conversation(matchId ?? ""),
    queryFn: () =>
      MIGRATE.messages
        ? api
            .get<BeMessagesResponse>(`/matches/${matchId}/messages`)
            .then((be) => mapConversation(be, matchId ?? ""))
        : api.get<ConversationResponse>(`/matches/${matchId}/messages`),
    enabled: Boolean(matchId),
  });
}
