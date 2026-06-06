import { useCallback, useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate, useParams } from "react-router-dom";
import { Menu, Search } from "lucide-react";
import { useConversation } from "@/api/endpoints/messages";
import { isValidUUID } from "@/lib/uuid";
import { MIGRATE } from "@/api/migration-flags";
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
import { PartnerProfileSheet } from "./components/PartnerProfileSheet";

type ConvState = {
  dateId?: string;
  partnerAgentId?: string;
  partnerName?: string;
  partnerAvatarUrl?: string;
};

export function ConversationPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const state = (useLocation().state as ConvState | null) ?? {};

  // 실 백엔드 모드에서 URL에 mock ID(mt_seed_001 등)가 남아있으면 /matches로 보낸다.
  if (MIGRATE.messages && !isValidUUID(matchId)) {
    return <Navigate to="/matches" replace />;
  }

  const { activeAgentId } = useAuth();
  const query = useConversation(matchId);

  const [live, setLive] = useState<ChatMessage[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  useEffect(() => setLive([]), [matchId]);

  const onFrame = useCallback((frame: WsFrame) => {
    const payload = frame.payload as ChatTopicEvent | undefined;
    if (payload?.kind === "message") {
      setLive((prev) => [...prev, payload.message]);
    }
  }, []);
  useTopic(matchId ? topics.chat(matchId) : null, onFrame);

  // date 토픽 구독 — date_ended 수신 시 결과 페이지로 이동
  const onDateFrame = useCallback(
    (frame: WsFrame) => {
      const ev = (frame.payload as { event?: string } | undefined)?.event;
      if (ev === "date_ended") {
        navigate(`/matches/${matchId}/result`, {
          state: {
            dateId: state.dateId,
            partnerAgentId: state.partnerAgentId,
            partnerName: state.partnerName,
            partnerAvatarUrl: state.partnerAvatarUrl,
          },
          replace: true,
        });
      }
    },
    [navigate, matchId, state],
  );
  useTopic(state.dateId ? topics.date(state.dateId) : null, onDateFrame);

  const handleSend = (text: string) => {
    if (!activeAgentId || !matchId) return;
    // Optimistic echo — backend persists the user message but only pushes the
    // agent's reply back over the chat topic.
    const optimistic: ChatMessage = {
      messageId: `local_${Date.now()}`,
      senderId: activeAgentId,
      type: "text",
      content: text,
      sentAt: new Date().toISOString(),
      readAt: null,
    };
    setLive((prev) => [...prev, optimistic]);
    wsClient.sendAction("send_message", {
      match_id: matchId,
      agent_id: activeAgentId,
      content: text,
    });
  };

  return (
    <QueryBoundary query={query}>
      {(data) => {
        // Date kinds were unified into a single "Date".
        const pillLabel = "Date";
        const merged: ChatMessage[] = [...data.messages, ...live];
        const partnerName = state.partnerName || data.matchInfo.partnerAgent.displayName;
        const partnerAgentId = state.partnerAgentId || data.matchInfo.partnerAgent.agentId;
        return (
          <>
            <MobileHeader
              showBack
              title={partnerName}
              action={
                <>
                  <span className="rounded-full bg-surface px-3 py-1 text-body2 font-semibold text-text shadow-card">
                    {pillLabel}
                  </span>
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
                <div className="text-center text-body1 text-text-subtle py-12">
                  No messages yet.
                </div>
              ) : (
                merged.map((m) => (
                  <MessageBubble key={m.messageId} mine={m.senderId === activeAgentId}>
                    {m.content}
                  </MessageBubble>
                ))
              )}
            </div>
            {/* Manual dates are user-driven — show the composer. Auto dates run
                between the agents, so no input. */}
            {data.matchInfo.matchType === "manual" ? (
              <ChatInput onSubmit={handleSend} />
            ) : null}
            <ConversationMenuSheet
              open={menuOpen}
              onOpenChange={setMenuOpen}
              partnerAgentId={partnerAgentId}
              task={data.matchInfo.task}
              onViewProfile={() => {
                setMenuOpen(false);
                setProfileOpen(true);
              }}
            />
            <PartnerProfileSheet
              agentId={partnerAgentId}
              open={profileOpen}
              onOpenChange={setProfileOpen}
            />
          </>
        );
      }}
    </QueryBoundary>
  );
}
