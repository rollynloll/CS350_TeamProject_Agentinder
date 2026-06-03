import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Menu, Search, Star } from "lucide-react";
import { useEndDate, useLiveDate } from "@/api/endpoints/dates";
import { useTopic } from "@/api/ws/hooks";
import { topics, type DateTopicEvent } from "@/api/ws/topics";
import type { WsFrame } from "@/api/types";
import { useAuth } from "@/store/auth";
import { MessageBubble } from "@/design-system/components/MessageBubble";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { ConversationMenuSheet } from "@/features/conversation/components/ConversationMenuSheet";
import { RatingSheet } from "./components/RatingSheet";

type LiveMessage = {
  messageId: string;
  senderId: string;
  content: string;
  sentAt: string;
};

const typeLabel: Record<string, string> = {
  coffee_chat: "Coffee Chat",
  activity_date: "Activity Date",
  deep_dive: "Deep Dive",
};

export function DateLivePage() {
  const { dateId } = useParams<{ dateId: string }>();
  const navigate = useNavigate();
  const { activeAgentId } = useAuth();
  const query = useLiveDate(dateId);
  const endDate = useEndDate(dateId ?? "");
  const [showRating, setShowRating] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const [streamed, setStreamed] = useState<LiveMessage[]>([]);
  useEffect(() => setStreamed([]), [dateId]);

  const onFrame = useCallback((frame: WsFrame) => {
    const payload = frame.payload as DateTopicEvent | undefined;
    if (payload?.kind === "date_message") {
      setStreamed((prev) => [...prev, payload.message]);
    }
  }, []);
  useTopic(dateId ? topics.date(dateId) : null, onFrame);

  return (
    <QueryBoundary query={query}>
      {(data) => {
        const merged = [...data.recentMessages, ...streamed];
        const pillLabel = typeLabel[data.type] ?? data.type;
        return (
          <>
            <MobileHeader
              showBack
              title={data.partnerAgent.displayName}
              action={
                <>
                  <span className="rounded-full bg-surface px-3 py-1 text-body2 font-semibold text-text shadow-card">
                    {pillLabel}
                  </span>
                  <button
                    type="button"
                    aria-label="Search in date"
                    className="grid place-items-center w-9 h-9 rounded-full bg-surface text-text shadow-card"
                  >
                    <Search className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setMenuOpen(true)}
                    aria-label="Open date menu"
                    className="grid place-items-center w-9 h-9 rounded-full text-text hover:bg-surface-2"
                  >
                    <Menu className="w-5 h-5" />
                  </button>
                </>
              }
            />
            <div className="relative flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-3">
              {merged.map((m) => (
                <MessageBubble
                  key={m.messageId}
                  mine={m.senderId === activeAgentId}
                >
                  {m.content}
                </MessageBubble>
              ))}
              <button
                type="button"
                onClick={() => setShowRating(true)}
                className="sticky bottom-2 ml-auto flex items-center gap-1.5 bg-primary text-primary-fg rounded-full px-4 py-2 text-body1 font-bold shadow-elevated hover:opacity-90 active:opacity-80 transition-opacity"
              >
                <Star className="w-4 h-4" fill="currentColor" strokeWidth={0} />
                Rate
              </button>
            </div>
            <RatingSheet
              open={showRating}
              onOpenChange={setShowRating}
              partnerName={data.partnerAgent.displayName}
              onSubmit={(d) => {
                if (!dateId) return;
                endDate.mutate(
                  {
                    action: "end",
                    outcome: d.outcome,
                    rating: d.rating,
                    compatibility: d.compatibility,
                    feedback: d.feedback,
                  },
                  { onSuccess: () => navigate("/matches") },
                );
              }}
            />
            <ConversationMenuSheet
              open={menuOpen}
              onOpenChange={setMenuOpen}
              partnerAgentId={data.partnerAgent.agentId}
            />
          </>
        );
      }}
    </QueryBoundary>
  );
}
