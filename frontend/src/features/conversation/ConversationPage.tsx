import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CalendarPlus, Menu, Search } from "lucide-react";
import { useConversation } from "@/api/endpoints/messages";
import { useScheduleDate } from "@/api/endpoints/dates";
import { useTopic } from "@/api/ws/hooks";
import { wsClient } from "@/api/ws/client";
import { topics, type ChatTopicEvent } from "@/api/ws/topics";
import type { ChatMessage, WsFrame } from "@/api/types";
import { useAuth } from "@/store/auth";
import { MessageBubble } from "@/design-system/components/MessageBubble";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { ChatInput } from "./components/ChatInput";
import { ConversationMenuSheet } from "./components/ConversationMenuSheet";
import { ScheduleDateSheet } from "./components/ScheduleDateSheet";

export function ConversationPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const { activeAgentId } = useAuth();
  const query = useConversation(matchId);
  const schedule = useScheduleDate(matchId ?? "");

  const [live, setLive] = useState<ChatMessage[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  useEffect(() => setLive([]), [matchId]);

  const onFrame = useCallback((frame: WsFrame) => {
    const payload = frame.payload as ChatTopicEvent | undefined;
    if (payload?.kind === "message") {
      setLive((prev) => [...prev, payload.message]);
    }
  }, []);
  useTopic(matchId ? topics.chat(matchId) : null, onFrame);

  const handleSend = (text: string) => {
    if (!activeAgentId || !matchId) return;
    // Optimistic echo — the backend persists the user message but does NOT push
    // it back over the chat topic (only the agent's reply is pushed).
    const optimistic: ChatMessage = {
      messageId: `local_${Date.now()}`,
      senderId: activeAgentId,
      type: "text",
      content: text,
      sentAt: new Date().toISOString(),
      readAt: null,
    };
    setLive((prev) => [...prev, optimistic]);
    // Send over WS — backend event "send_message" → saves + generates a reply
    // pushed back on chat.{matchId}, which onFrame appends above.
    wsClient.sendAction("send_message", {
      match_id: matchId,
      agent_id: activeAgentId,
      content: text,
    });
  };

  return (
    <QueryBoundary query={query}>
      {(data) => {
        // Coffee Chat vs Date pill — stand-in until API spec adds activeDateType.
        const pillLabel = data.matchInfo.canScheduleDate ? "Coffee Chat" : "Date";
        const merged: ChatMessage[] = [...data.messages, ...live];
        return (
          <>
            <MobileHeader
              showBack
              title={data.matchInfo.partnerAgent.displayName}
              action={
                <>
                  <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-text shadow-card">
                    {pillLabel}
                  </span>
                  {data.matchInfo.canScheduleDate ? (
                    <button
                      type="button"
                      onClick={() => setScheduleOpen(true)}
                      aria-label="Schedule a date"
                      className="grid place-items-center w-9 h-9 rounded-full bg-surface text-text shadow-card"
                    >
                      <CalendarPlus className="w-4 h-4" />
                    </button>
                  ) : null}
                  <button
                    type="button"
                    aria-label="Search in conversation"
                    className="grid place-items-center w-9 h-9 rounded-full bg-surface text-text shadow-card"
                  >
                    <Search className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setMenuOpen(true)}
                    aria-label="Open conversation menu"
                    className="grid place-items-center w-9 h-9 rounded-full text-text hover:bg-surface-2"
                  >
                    <Menu className="w-5 h-5" />
                  </button>
                </>
              }
            />
            <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-3">
              {merged.length === 0 ? (
                <div className="text-center text-sm text-text-subtle py-12">
                  No messages yet.
                </div>
              ) : (
                merged.map((m) => (
                  <MessageBubble
                    key={m.messageId}
                    mine={m.senderId === activeAgentId}
                  >
                    {m.content}
                  </MessageBubble>
                ))
              )}
            </div>
            <ChatInput onSubmit={handleSend} />
            <ConversationMenuSheet
              open={menuOpen}
              onOpenChange={setMenuOpen}
              partnerAgentId={data.matchInfo.partnerAgent.agentId}
              matchId={data.matchInfo.matchId}
            />
            <ScheduleDateSheet
              open={scheduleOpen}
              onOpenChange={setScheduleOpen}
              submitting={schedule.isPending}
              onSubmit={(d) => {
                schedule.mutate(
                  { type: d.type, proposedTime: new Date(d.proposedTime).toISOString() },
                  {
                    onSuccess: (res) => {
                      setScheduleOpen(false);
                      navigate(`/dates/${res.dateId}`);
                    },
                  },
                );
              }}
            />
          </>
        );
      }}
    </QueryBoundary>
  );
}
