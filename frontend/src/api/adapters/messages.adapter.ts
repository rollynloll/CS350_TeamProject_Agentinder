import type { ChatMessage, ConversationResponse, MatchId } from "../types";
import type { BeMessage, BeMessagesResponse } from "./backend-types";
import { avatarOrFallback, partnerLabel } from "./defaults";

function mapMessage(be: BeMessage): ChatMessage {
  return {
    messageId: be.message_id,
    senderId: be.sender_agent_id,
    type: "text",
    content: be.content,
    sentAt: be.created_at,
    readAt: be.is_read ? be.created_at : null,
  };
}

// Backend messages endpoint returns only the message list (items already
// oldest->newest). Match/partner metadata is synthesized.
export function mapConversation(be: BeMessagesResponse, matchId: MatchId): ConversationResponse {
  return {
    matchInfo: {
      matchId,
      partnerAgent: {
        agentId: "",
        displayName: partnerLabel(matchId),
        avatarUrl: avatarOrFallback(null, matchId),
        trustScore: null,
      },
      tier: "stranger",
      canScheduleDate: true,
      canSendMultimedia: false,
      matchType: "manual",
    },
    messages: (be.items ?? []).map(mapMessage),
  };
}
