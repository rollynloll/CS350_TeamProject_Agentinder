// WebSocket topic helpers — spec §4.3
import type { AgentId, ChatMessage, DateId, MatchId, MessageId } from "../types";

export const topics = {
  matches: (agentId: AgentId) => `matches.${agentId}`,
  chat: (matchId: MatchId) => `chat.${matchId}`,
  date: (dateId: DateId) => `date.${dateId}`,
};

// Event payload shapes (incoming server → client)

export type MatchTopicEvent =
  | {
      kind: "new_match";
      matchId: MatchId;
      partnerAgent: { agentId: AgentId; displayName: string; avatarUrl: string };
      icebreakers: string[];
    }
  | { kind: "match_updated"; matchId: MatchId; changes: Record<string, unknown> }
  | {
      kind: "message_preview";
      matchId: MatchId;
      preview: string;
      senderId: AgentId;
      sentAt: string;
    };

export type ChatTopicEvent =
  | { kind: "message"; message: ChatMessage }
  | { kind: "typing"; senderId: AgentId; isTyping: boolean }
  | { kind: "read"; readerId: AgentId; lastReadMessageId: MessageId };

export type DateTopicEvent =
  | {
      kind: "date_message";
      message: { messageId: MessageId; senderId: AgentId; content: string; sentAt: string };
    }
  | { kind: "icebreaker_prompt"; prompt: string }
  | { kind: "time_warning"; remainingMinutes: number }
  | { kind: "date_ended"; outcome: string; endedBy: AgentId };

// Client → server actions
export type ChatAction =
  | { kind: "send_message"; type: "text"; content: string }
  | { kind: "mark_read"; lastReadMessageId: MessageId }
  | { kind: "typing_start" }
  | { kind: "typing_stop" };

export type DateAction =
  | { kind: "send_date_message"; content: string }
  | { kind: "end_date"; outcome: string; rating: number; feedback?: string };
