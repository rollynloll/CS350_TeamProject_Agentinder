import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { ConversationResponse, MatchId } from "../types";
import { MIGRATE } from "../migration-flags";
import { mapConversation } from "../adapters";
import type { BeMessagesResponse } from "../adapters";
import { isValidUUID } from "@/lib/uuid";

export const messageKeys = {
  all: ["messages"] as const,
  conversation: (matchId: MatchId) => ["messages", matchId] as const,
};

export function useConversation(matchId: MatchId | undefined) {
  // 실 백엔드는 match_id를 UUID로 파싱하므로, 유효한 UUID가 아닌 경우(mock ID 등)
  // 쿼리를 비활성화해 422를 방지한다.
  const enabled = MIGRATE.messages ? isValidUUID(matchId) : Boolean(matchId);
  return useQuery({
    queryKey: messageKeys.conversation(matchId ?? ""),
    queryFn: () =>
      MIGRATE.messages
        ? api
            .get<BeMessagesResponse>(`/matches/${matchId}/messages`)
            .then((be) => mapConversation(be, matchId ?? ""))
        : api.get<ConversationResponse>(`/matches/${matchId}/messages`),
    enabled,
  });
}
